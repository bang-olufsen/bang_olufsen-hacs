"""Halo client."""

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
import contextlib
import json
import logging

from aiohttp import ClientSession, ClientTimeout, WSMessageTypeError
from aiohttp.client_exceptions import (
    ClientConnectorError,
    ClientOSError,
    ServerTimeoutError,
)
from inflection import underscore

from .const import WEBSOCKET_TIMEOUT
from .models import (
    BaseConfiguration,
    BaseWebSocketResponse,
    Button,
    ButtonEvent,
    Configuration,
    Event,
    EventType,
    PowerEvent,
    StatusEvent,
    SystemEvent,
    Update,
    UpdateButton,
    WheelEvent,
)


class Halo:
    """Beoremote Halo client."""

    def __init__(
        self,
        host: str,
        configuration: BaseConfiguration = BaseConfiguration(Configuration([])),
    ) -> None:
        """Initialize Halo client.

        Args:
            host: IPv4 address.
            configuration: Halo configuration. Defaults to `BaseConfiguration(Configuration([]))`.

        """
        self.host = host
        self.websocket_connected = False
        self.websocket_reconnect = False

        self._configuration = configuration

        self._websocket_active = False
        self._websocket_task: asyncio.Task
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._on_connection_lost: Callable[[None], Awaitable[None] | None] | None = None
        self._on_connection: Callable[[None], Awaitable[None] | None] | None = None

        self._on_all_events: Callable | None = None
        self._on_all_events_raw: Callable | None = None

        self._event_callbacks: dict[str, Callable | None] = defaultdict()
        self._event_callbacks.default_factory = lambda: None

        self._logger = logging.getLogger(__name__)

    def _send_data(self, data: BaseConfiguration | Update) -> bool:
        """Send data to the Beoremote Halo.

        Args:
            data: `Configuration` or `Update`.

        Returns:
            If the data was successfully put into WebSocket queue.

        """
        if not self._websocket_active:
            self._logger.debug(
                "Unable to send %s. WebSocket connection not active", data
            )
            return False

        try:
            self._queue.put_nowait(str(data.to_json()))
        except (asyncio.QueueFull, asyncio.QueueShutDown):
            return False
        else:
            return True

    @property
    def configuration(self) -> BaseConfiguration:
        """Get configuration."""
        return self._configuration

    async def set_configuration(
        self, configuration: BaseConfiguration | None, send_configuration: bool = True
    ) -> bool:
        """Set configuration.

        Setting configuration to be `None` will set the configuration to be `BaseConfiguration(Configuration([]))`.

        Args:
            configuration: Configuration to set/send.
            send_configuration: Send configuration to Halo. Requires WebSocket connection to be active.. Defaults to True.

        Returns:
            If the configuration was successfully put into WebSocket queue.

        """
        self._configuration = (
            BaseConfiguration(Configuration([]))
            if configuration is None
            else configuration
        )

        if send_configuration:
            return self._send_data(self._configuration)
        return False

    async def update(self, update: Update, update_configuration: bool = True) -> bool:
        """Send update to Halo. Requires WebSocket connection to be active.

        Args:
            update: Update event to be sent.
            update_configuration: If the configuration should be modified with passed `UpdateButton` values. Defaults to True.

        Returns:
            If the update was successfully put into WebSocket queue.

        """
        if update_configuration and isinstance(update.update, UpdateButton):
            # Try to get indices for button and update configuration
            if indices := self.get_page_and_button_index(update.update.id):
                page_idx, button_idx = indices

                self._configuration.configuration.pages[page_idx].buttons[
                    button_idx
                ].state = update.update.state

                self._configuration.configuration.pages[page_idx].buttons[
                    button_idx
                ].value = update.update.value
            else:
                self._logger.debug(
                    "Unable to find %s in configuration", update.update.id
                )

        return self._send_data(update)

    async def check_device_connection(self, raise_error: bool = False) -> bool:
        """Check WebSocket connection.

        Args:
            raise_error: Raise any errors. Defaults to False.

        Returns:
            Connection successful

        """
        try:
            async with (
                ClientSession(
                    timeout=ClientTimeout(connect=WEBSOCKET_TIMEOUT)
                ) as session,
                session.ws_connect(f"ws://{self.host}:8080/") as websocket,
            ):
                if await websocket.receive():
                    return True
        except (
            ClientConnectorError,
            ClientOSError,
            ServerTimeoutError,
            WSMessageTypeError,
        ) as error:
            if raise_error:
                raise
            self._logger.error(
                "Unable to connect to %s : %s - %s", self.host, type(error), error
            )
            return False

    async def connect(
        self, reconnect: bool = False, send_configuration: bool = True
    ) -> None:
        """Start WebSocket connection.

        Will start listening for events and allow updates to be sent.

        Args:
            reconnect: Whether or not to reconnect. Defaults to False.
            send_configuration: Whether to automatically send configuration on connect/reconnect. Defaults to True.

        """
        self.websocket_reconnect = reconnect

        if not self._websocket_active:
            self._websocket_task = asyncio.create_task(
                coro=self._websocket_connection(
                    f"ws://{self.host}:8080/", send_configuration
                ),
                name=f"{self.host} - task",
            )

            self._websocket_active = True
        else:
            self._logger.error("WebSocket task already active")

    async def disconnect(self) -> None:
        """Stop WebSocket connection."""
        self._websocket_active = False
        self._websocket_task.cancel()

    async def _websocket_connection(
        self, host: str, send_configuration: bool = True
    ) -> None:
        """WebSocket connection handler.

        Args:
            host: IPV4 address to connect to.
            send_configuration: Whether to automatically send configuration on connect/reconnect. Defaults to True.

        """
        while True:
            try:
                async with (
                    ClientSession(
                        timeout=ClientTimeout(connect=WEBSOCKET_TIMEOUT)
                    ) as session,
                    session.ws_connect(
                        url=host, heartbeat=WEBSOCKET_TIMEOUT
                    ) as websocket,
                ):
                    self.websocket_connected = True

                    # Send configuration
                    if send_configuration:
                        self._send_data(self._configuration)

                    if self._on_connection:
                        await self._trigger_callback(self._on_connection)

                    while self._websocket_active:
                        # Receive events
                        with contextlib.suppress(asyncio.TimeoutError):
                            event = await websocket.receive_str(timeout=0.1)
                            await self._on_message(event)

                        # Send updates
                        with contextlib.suppress(asyncio.QueueEmpty):
                            await websocket.send_str(self._queue.get_nowait())

                    self.websocket_connected = False
                    await websocket.close()
                    return

            except (
                ClientConnectorError,
                ClientOSError,
                TypeError,
                ServerTimeoutError,
                WSMessageTypeError,
            ) as error:
                if self.websocket_connected:
                    self._logger.debug("%s : %s - %s", host, type(error), error)
                    self.websocket_connected = False

                    if self._on_connection_lost:
                        await self._trigger_callback(self._on_connection_lost)

                if not self.websocket_reconnect:
                    self._logger.error("%s : %s - %s", host, type(error), error)
                    await self.disconnect()
                    return

                await asyncio.sleep(WEBSOCKET_TIMEOUT)

    async def _on_message(self, event: str) -> None:
        """Handle WebSocket events."""
        # Get the object type and deserialized object.
        try:
            deserialized_data = Event.from_json(event).event
        except (ValueError, AttributeError) as error:
            self._logger.error(
                "%s unable to deserialize WebSocket event: (%s) with error: (%s : %s)",
                self.host,
                event,
                type(error),
                error,
            )
            return

        # Handle all events if defined
        if self._on_all_events:
            await self._trigger_callback(
                self._on_all_events,
                deserialized_data,
                underscore(deserialized_data.type),
            )

        if self._on_all_events_raw:
            await self._trigger_callback(self._on_all_events_raw, json.loads(event))

        # Handle specific events if defined
        triggered_event = self._event_callbacks[deserialized_data.type]

        if triggered_event:
            await self._trigger_callback(triggered_event, deserialized_data)

    async def _trigger_callback(
        self,
        callback: Callable,
        *args: BaseWebSocketResponse | dict | str | EventType,
    ) -> None:
        """Trigger async or sync callback correctly."""
        if asyncio.iscoroutinefunction(callback):
            await callback(*args)
        else:
            callback(*args)

    def get_on_connection_lost(self, on_connection_lost: Callable) -> None:
        """Set callback for WebSocket connection lost."""
        self._on_connection_lost = on_connection_lost

    def get_on_connection(self, on_connection: Callable) -> None:
        """Set callback for WebSocket connection."""
        self._on_connection = on_connection

    def get_all_events(
        self,
        on_all_events: Callable[[EventType, str], Awaitable[None] | None],
    ) -> None:
        """Set callback for all events."""
        self._on_all_events = on_all_events

    def get_all_events_raw(
        self,
        on_all_events_raw: Callable[[BaseWebSocketResponse], Awaitable[None] | None],
    ) -> None:
        """Set callback for all events as dict."""
        self._on_all_events_raw = on_all_events_raw

    def get_wheel_event(
        self, on_wheel_event: Callable[[WheelEvent], Awaitable[None] | None]
    ) -> None:
        """Set callback for WheelEvent."""
        self._event_callbacks["wheel"] = on_wheel_event

    def get_system_event(
        self, on_system_event: Callable[[SystemEvent], Awaitable[None] | None]
    ) -> None:
        """Set callback for SystemEvent."""
        self._event_callbacks["system"] = on_system_event

    def get_status_event(
        self, on_status_event: Callable[[StatusEvent], Awaitable[None] | None]
    ) -> None:
        """Set callback for StatusEvent."""
        self._event_callbacks["status"] = on_status_event

    def get_power_event(
        self, on_power_event: Callable[[PowerEvent], Awaitable[None] | None]
    ) -> None:
        """Set callback for PowerEvent."""
        self._event_callbacks["power"] = on_power_event

    def get_button_event(
        self, on_button_event: Callable[[ButtonEvent], Awaitable[None] | None]
    ) -> None:
        """Set callback for ButtonEvent."""
        self._event_callbacks["button"] = on_button_event

    # Configuration helper methods
    def get_page_and_button_index(self, button_id: str) -> tuple[int, int] | None:
        """Get `Page` and `Button` indices in configuration from `Button` ID.

        Returns:
            `Page` index, `Button` index or `None` if button_id can't be found.

        """
        for page_idx, page in enumerate(self._configuration.configuration.pages):
            for button_idx, button in enumerate(page.buttons):
                if button.id == button_id:
                    return (page_idx, button_idx)
        return None

    def get_button_from_id(self, button_id: str) -> Button | None:
        """Get `Button` in configuration from `Button` ID.

        Returns:
            `Button` or None if `Button` can't be found.

        """
        for page in self._configuration.configuration.pages:
            for button in page.buttons:
                if button.id == button_id:
                    return button
        return None

    def get_default_button_id(self) -> str | None:
        """Get the default `Button` ID from configuration if available.

        Returns:
            `Button` ID or None.

        """
        for page in self._configuration.configuration.pages:
            for button in page.buttons:
                if button.default is True:
                    return button.id
        return None
