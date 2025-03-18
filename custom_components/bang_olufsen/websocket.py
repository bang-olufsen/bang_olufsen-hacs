"""WebSocket listener(s) for the Bang & Olufsen integration."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import contextlib
from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING

from mozart_api.models import (
    BatteryState,
    BeoRemoteButton,
    ButtonEvent,
    ListeningModeProps,
    PlaybackContentMetadata,
    PlaybackError,
    PlaybackProgress,
    RenderingState,
    SoftwareUpdateState,
    Source,
    SpeakerGroupOverview,
    VolumeState,
    WebsocketNotificationTag,
)
from mozart_api.mozart_client import BaseWebSocketResponse, MozartClient
import numpy as np
from voluptuous import Invalid

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN
from homeassistant.components.input_button import DOMAIN as INPUT_BUTTON_DOMAIN
from homeassistant.components.input_number import DOMAIN as INPUT_NUMBER_DOMAIN
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_BRIGHTNESS_STEP_PCT,
    DOMAIN as LIGHT_DOMAIN,
)
from homeassistant.components.number import (
    ATTR_MAX,
    ATTR_MIN,
    ATTR_STEP,
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_ENTITY_ID,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util.enum import try_parse_enum

from .const import (
    CONF_ENTITY_MAP,
    CONF_HALO,
    CONNECTION_STATUS,
    EVENT_TRANSLATION_MAP,
    HALO_WEBSOCKET_EVENT,
    HALO_WHEEL_TIMEOUT,
    MOZART_WEBSOCKET_EVENT,
    BangOlufsenModel,
    WebsocketNotification,
)
from .entity import HaloBase, MozartBase
from .halo import (
    MAX_VALUE,
    MIN_VALUE,
    BaseConfiguration,
    BaseUpdate,
    BaseWebSocketResponse as HaloBaseWebSocketResponse,
    Button,
    ButtonEvent as HaloButtonEvent,
    ButtonEventState,
    ButtonState,
    Halo,
    PowerEvent,
    StatusEvent,
    SystemEvent,
    UpdateButton,
    WheelEvent,
)
from .util import get_remotes

_LOGGER = logging.getLogger(__name__)


@dataclass
class WheelCounter:
    """Store Task and counter for wheel event service calls."""

    timer: asyncio.TimerHandle | None = None
    counter: int = 0


class HaloWebsocket(HaloBase):
    """WebSocket for Halo."""

    _configuration: BaseConfiguration | None = None
    _entity_map: dict[str, str] = {}
    _wheel_action_handlers: dict[str, WheelCounter] = {}

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: Halo,
    ) -> None:
        """Initialize the entity coordinator."""
        super().__init__(config_entry, client)

        self.hass = hass
        self._device = self.get_device(hass, self._unique_id)
        self._entity_registry = er.async_get(self.hass)

        if TYPE_CHECKING:
            assert isinstance(self._client, Halo)

        self._client.get_button_event(self.on_button_event)
        self._client.get_on_connection_lost(self.on_connection_lost)
        self._client.get_on_connection(self.on_connection)
        self._client.get_power_event(self.on_power_event)
        self._client.get_status_event(self.on_status_event)
        self._client.get_system_event(self.on_system_event)
        self._client.get_wheel_event(self.on_wheel_event)

        self._client.get_all_events_raw(self.on_all_events_raw)

        # Track entity changes to sync with Halo configuration
        if config_entry.options:
            self._entity_map = config_entry.options[CONF_ENTITY_MAP]

            entity_ids = set(self._entity_map.values())
            async_track_state_change_event(
                self.hass,
                entity_ids,
                self._handle_entity_state_change,
            )
            # Handle configuration
            self._configuration = BaseConfiguration.from_dict(
                self.entry.options[CONF_HALO]
            )
            # Create wheel counters
            self._wheel_action_handlers = {
                entity_id: WheelCounter() for entity_id in entity_ids
            }

        # Dict for associating platforms with update methods
        self._entity_update_map: dict[str, Callable] = {
            BINARY_SENSOR_DOMAIN: self._handle_binary_update,
            BUTTON_DOMAIN: self._handle_button_update,
            INPUT_BOOLEAN_DOMAIN: self._handle_binary_update,
            INPUT_BUTTON_DOMAIN: self._handle_button_update,
            INPUT_NUMBER_DOMAIN: self._handle_number_sensor_update,
            LIGHT_DOMAIN: self._handle_light_update,
            NUMBER_DOMAIN: self._handle_number_sensor_update,
            SENSOR_DOMAIN: self._handle_number_sensor_update,
            SWITCH_DOMAIN: self._handle_binary_update,
        }

        # Dict for associating platforms with button methods
        self._entity_button_action_map: dict[str, Callable] = {
            BINARY_SENSOR_DOMAIN: self._handle_no_button_action,
            BUTTON_DOMAIN: self._handle_button_button_action,
            INPUT_BOOLEAN_DOMAIN: self._handle_binary_button_action,
            INPUT_BUTTON_DOMAIN: self._handle_button_button_action,
            INPUT_NUMBER_DOMAIN: self._handle_number_button_action,
            LIGHT_DOMAIN: self._handle_light_button_action,
            NUMBER_DOMAIN: self._handle_number_button_action,
            SENSOR_DOMAIN: self._handle_no_button_action,
            SWITCH_DOMAIN: self._handle_binary_button_action,
        }

        # Dict for associating platforms with wheel methods
        self._entity_wheel_callback_map: dict[str, Callable] = {
            BINARY_SENSOR_DOMAIN: self._handle_no_wheel_action,
            BUTTON_DOMAIN: self._handle_no_wheel_action,
            INPUT_BOOLEAN_DOMAIN: self._handle_switch_wheel_action_callback,
            INPUT_BUTTON_DOMAIN: self._handle_no_wheel_action,
            INPUT_NUMBER_DOMAIN: self._handle_number_wheel_action_callback,
            LIGHT_DOMAIN: self._handle_light_wheel_action_callback,
            NUMBER_DOMAIN: self._handle_number_wheel_action_callback,
            SENSOR_DOMAIN: self._handle_no_wheel_action,
            SWITCH_DOMAIN: self._handle_switch_wheel_action_callback,
        }

    def _get_button_from_id(self, button_id: str) -> Button | None:
        """Get Button from button_id."""
        if self._configuration is not None:
            for page in self._configuration.configuration.pages:
                for button in page.buttons:
                    if button.id == button_id:
                        return button
        return None

    def _update_configuration(
        self, button_id: str, button_state: ButtonState, button_value: int
    ) -> None:
        """Update Configuration with a button's current value."""
        if TYPE_CHECKING:
            assert self._configuration

        for page_idx, page in enumerate(self._configuration.configuration.pages):
            for button_idx, button in enumerate(page.buttons):
                if button.id == button_id:
                    self._configuration.configuration.pages[page_idx].buttons[
                        button_idx
                    ].state = button_state

                    self._configuration.configuration.pages[page_idx].buttons[
                        button_idx
                    ].value = button_value

        # TO DO: Evaluate when config_entry options should be updated
        # new_entry_data = dict(self._entry.options)
        # new_entry_data[CONF_HALO] = self._configuration.to_dict()

        # self.hass.config_entries.async_update_entry(self._entry, options=new_entry_data)

    def _clamp_value(self, value: int) -> int:
        """Clamp a value to work with Halo value."""
        return int(np.clip(value, MIN_VALUE, MAX_VALUE))

    async def _handle_no_button_action(
        self, entity_state: State, button_id: str
    ) -> None:
        """Handle entity with no associated button action."""
        _LOGGER.debug("No button action available for %s", entity_state.entity_id)

    def _handle_no_wheel_action(self, entity_state: State) -> None:
        """Handle entity with no associated wheel action."""
        _LOGGER.debug("No wheel action available for %s", entity_state.entity_id)

    async def _update_entity_button_values(self, entity_id: str) -> None:
        """Send Halo Button configuration updates of current entity states."""
        # Get the button ids
        button_ids = []
        for mapped_button_id, mapped_entity_id in self._entity_map.items():
            if mapped_entity_id == entity_id:
                button_ids.append(mapped_button_id)

        # Handle update for pages that the entity is present on
        for button_id in button_ids:
            await self._handle_entity_update(entity_id, button_id)

    async def _handle_entity_state_change(
        self,
        event: Event[EventStateChangedData],
    ) -> None:
        """Handle state change of entities."""
        entity_id = event.data[CONF_ENTITY_ID]

        if entity_id not in self._entity_map.values():
            logging.error("Entity %s is not in entity map")
            return

        await self._update_entity_button_values(entity_id)

    # TO DO handle entity deletion

    async def _handle_entity_update(self, entity_id: str, button_id: str) -> None:
        """Handle state change events of entities."""

        entity_state = self.hass.states.get(entity_id)
        if entity_state is None:
            _LOGGER.debug("Error retrieving state for %s", entity_id)
            return

        try:
            button_state, button_value = self._entity_update_map[entity_state.domain](
                entity_state
            )
        except KeyError:
            _LOGGER.error(
                "The Halo does not handle %s platform Button state updates yet",
                entity_state.domain,
            )
            return

        # Get button from Halo configuration
        if (button := self._get_button_from_id(button_id)) is None:
            _LOGGER.error("Unable to retrieve Halo button for %s", entity_id)
            return

        # Avoid unnecessary updates when Home Assistant is started if nothing has changed
        if button.state == button_state and button.value == button_value:
            _LOGGER.debug(
                "Skipping update for %s button on",
                button.title,
            )
            return

        # Update configuration
        self._update_configuration(button.id, button_state, button_value)

        # Send update to Halo
        await self._client.send(
            BaseUpdate(update=UpdateButton(button.id, button_state, button_value))
        )

    async def _handle_entity_button_action(self, button_id: str) -> None:
        """Handle actions of entities."""

        # Get entity_id
        try:
            entity_id = self._entity_map[button_id]
        except KeyError:
            _LOGGER.error(
                "Error associating button %s with an entity id. Entity map %s",
                button_id,
                self._entity_map,
            )
            return

        entity_state = self.hass.states.get(entity_id)
        if entity_state is None:
            _LOGGER.error("Error retrieving state for %s", entity_id)
            return

        try:
            await self._entity_button_action_map[entity_state.domain](
                entity_state, button_id
            )
        except KeyError:
            _LOGGER.error(
                "The Halo does not handle %s platform Button actions yet",
                entity_state.domain,
            )
            return

    async def _handle_entity_wheel_action(self, button_id: str, counts: int) -> None:
        """Handle actions of entities."""

        # Get entity_id
        try:
            entity_id = self._entity_map[button_id]
        except KeyError:
            _LOGGER.error(
                "Error associating button %s with an entity id. Entity map %s",
                button_id,
                self._entity_map,
            )
            return

        entity_state = self.hass.states.get(entity_id)
        if entity_state is None:
            _LOGGER.error("Error retrieving state for %s", entity_id)
            return

        try:
            # Increment or decrement counter
            self._wheel_action_handlers[entity_state.entity_id].counter += counts

            # Cancel any scheduled action calls
            if (
                timer := self._wheel_action_handlers[entity_state.entity_id].timer
            ) is not None:
                timer.cancel()

            # Schedule a new action call
            self._wheel_action_handlers[
                entity_state.entity_id
            ].timer = self.hass.loop.call_later(
                HALO_WHEEL_TIMEOUT,
                self._entity_wheel_callback_map[entity_state.domain],
                entity_state,
            )

        except KeyError:
            _LOGGER.error(
                "The Halo does not handle %s platform Wheel actions yet",
                entity_state.domain,
            )
            return

    def _handle_number_sensor_update(self, state: State) -> tuple[ButtonState, int]:
        """Handle state change events of Number and Sensor entities."""
        try:
            converted_state = int(float(state.state))

            if (
                {"min", "max"}.issubset(state.attributes)
                and state.attributes[ATTR_MIN] != 0
                and state.attributes[ATTR_MAX] != 100
            ):
                converted_state = int(
                    np.interp(
                        converted_state,
                        [state.attributes[ATTR_MIN], state.attributes[ATTR_MAX]],
                        [MIN_VALUE, MAX_VALUE],
                    )
                )
            else:
                converted_state = self._clamp_value(converted_state)

        except ValueError:
            _LOGGER.exception("Error when handling number or sensor state %s", state)

            button_state = ButtonState.INACTIVE
            button_value = 0

        else:
            # Process the on/off state for a number
            button_state = (
                ButtonState.ACTIVE if converted_state > 50 else ButtonState.INACTIVE
            )
            # Process the value state for a sensor
            button_value = converted_state

        return (button_state, button_value)

    async def _handle_number_button_action(
        self, entity_state: State, button_id: str
    ) -> None:
        """Handle Number Button entity button actions."""
        if (button := self._get_button_from_id(button_id)) is None:
            _LOGGER.error(
                "Unable to retrieve Halo button for %s", entity_state.entity_id
            )
            return

        if button.state == ButtonState.ACTIVE:
            if "min" in entity_state.attributes:
                new_state = entity_state.attributes[ATTR_MIN]
            else:
                new_state = MIN_VALUE
        elif button.state == ButtonState.INACTIVE:
            if "max" in entity_state.attributes:
                new_state = entity_state.attributes[ATTR_MAX]
            else:
                new_state = MAX_VALUE

        _LOGGER.debug(
            "Sending %s to %s with value %s",
            SERVICE_SET_VALUE,
            entity_state.entity_id,
            new_state,
        )

        await self.hass.services.async_call(
            entity_state.domain,
            SERVICE_SET_VALUE,
            {
                ATTR_ENTITY_ID: entity_state.entity_id,
                ATTR_VALUE: new_state,
            },
        )

    def _handle_number_wheel_action_callback(self, entity_state: State) -> None:
        """Handle Number entity wheel action callback."""

        # Add the step value
        if "step" in entity_state.attributes:
            new_number = float(entity_state.state) + (
                entity_state.attributes[ATTR_STEP]
                * self._wheel_action_handlers[entity_state.entity_id].counter
            )
        else:
            new_number = float(entity_state.state) + (
                1 * self._wheel_action_handlers[entity_state.entity_id].counter
            )

        # Clamp the value if possible
        if {"min", "max"}.issubset(entity_state.attributes):
            new_number = int(
                np.clip(
                    new_number,
                    entity_state.attributes[ATTR_MIN],
                    entity_state.attributes[ATTR_MAX],
                )
            )

        if new_number == 0:
            return

        # Wrap action call in a task as callbacks can't be async
        asyncio.create_task(
            self._handle_number_wheel_action_task(entity_state, new_number)
        ).done()

    async def _handle_number_wheel_action_task(
        self, entity_state: State, new_number: int
    ) -> None:
        """Execute Number wheel action call."""
        _LOGGER.debug(
            "Sending %s to %s with value %s",
            SERVICE_SET_VALUE,
            entity_state.entity_id,
            new_number,
        )
        # Suppress any exceptions for now
        with contextlib.suppress(Invalid):
            await self.hass.services.async_call(
                entity_state.domain,
                SERVICE_SET_VALUE,
                {
                    ATTR_ENTITY_ID: entity_state.entity_id,
                    ATTR_VALUE: new_number,
                },
            )

        # Reset counter and timer
        self._wheel_action_handlers[entity_state.entity_id].counter = 0
        self._wheel_action_handlers[entity_state.entity_id].timer = None

    def _handle_binary_update(self, state: State) -> tuple[ButtonState, int]:
        """Handle state change events of Input Boolean, Switch and Binary Sensor entities."""

        # Process the on/off state for a input boolean switch / binary sensor
        try:
            button_state = (
                ButtonState.ACTIVE if state.state == STATE_ON else ButtonState.INACTIVE
            )
            button_value = 100 if state.state == STATE_ON else 0
        except ValueError:
            _LOGGER.exception(
                "Error when handling switch or binary_sensor state %s", state
            )

            button_state = ButtonState.INACTIVE
            button_value = 0

        return (button_state, button_value)

    async def _handle_binary_button_action(self, entity_state: State, _: str) -> None:
        """Handle Input Boolean and switch Button entity actions."""
        _LOGGER.debug("Sending %s to %s", SERVICE_SET_VALUE, entity_state.entity_id)

        await self.hass.services.async_call(
            entity_state.domain,
            SERVICE_TOGGLE,
            {ATTR_ENTITY_ID: entity_state.entity_id},
        )

    def _handle_switch_wheel_action_callback(self, entity_state: State) -> None:
        """Handle Switch entity wheel action callback."""

        # Ensure valid and not-useless action value
        if (
            entity_state.state == STATE_ON
            and self._wheel_action_handlers[entity_state.entity_id].counter <= -15
        ):
            action = SERVICE_TURN_OFF
        elif (
            entity_state.state == STATE_OFF
            and self._wheel_action_handlers[entity_state.entity_id].counter >= 15
        ):
            action = SERVICE_TURN_ON
        else:
            return

        # Wrap action call in a task as callbacks can't be async
        asyncio.create_task(
            self._handle_switch_wheel_action_task(entity_state, action)
        ).done()

    async def _handle_switch_wheel_action_task(
        self, entity_state: State, action: str
    ) -> None:
        """Execute Switch wheel action call."""
        _LOGGER.debug("Sending %s to %s", action, entity_state.entity_id)

        await self.hass.services.async_call(
            entity_state.domain,
            action,
            {ATTR_ENTITY_ID: entity_state.entity_id},
        )

        # Reset counter and timer
        self._wheel_action_handlers[entity_state.entity_id].counter = 0
        self._wheel_action_handlers[entity_state.entity_id].timer = None

    def _handle_button_update(self, _: State) -> tuple[ButtonState, int]:
        """Handle state change events of Input Button and Button entities."""
        # Currently do nothing when a button has been pressed.
        # Ideally there would be some indication, but it is cumbersome for now.
        return (ButtonState.INACTIVE, 0)

    async def _handle_button_button_action(self, entity_state: State, _: str) -> None:
        """Handle Button entity button actions."""
        _LOGGER.debug("Sending %s to %s", SERVICE_PRESS, entity_state.entity_id)

        await self.hass.services.async_call(
            entity_state.domain,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: entity_state.entity_id},
        )

    def _handle_light_update(self, state: State) -> tuple[ButtonState, int]:
        """Handle state change events of Light entities."""
        try:
            brightness = (
                state.attributes[ATTR_BRIGHTNESS]
                if state.attributes[ATTR_BRIGHTNESS] is not None
                else 0
            )
            # Brightness does not go to 255?
            converted_state = int(
                np.interp(
                    brightness,
                    [0, 254],
                    [MIN_VALUE, MAX_VALUE],
                )
            )
        except ValueError:
            _LOGGER.exception("Error when handling light state %s", state)

            button_state = ButtonState.INACTIVE
            button_value = 0

        else:
            # Process the on/off state for a light
            button_state = (
                ButtonState.ACTIVE if state.state == "on" else ButtonState.INACTIVE
            )
            # Process the value state for a light
            button_value = converted_state

        return (button_state, button_value)

    async def _handle_light_button_action(self, entity_state: State, _: str) -> None:
        """Handle Light entity button actions."""
        _LOGGER.debug("Sending %s to %s", SERVICE_TOGGLE, entity_state.entity_id)

        await self.hass.services.async_call(
            entity_state.domain,
            SERVICE_TOGGLE,
            {ATTR_ENTITY_ID: entity_state.entity_id},
        )

    def _handle_light_wheel_action_callback(self, entity_state: State) -> None:
        """Handle Light entity wheel action callback."""

        # Ensure valid and not-useless action value
        brightness_step = int(
            np.clip(
                self._wheel_action_handlers[entity_state.entity_id].counter, -100, 100
            )
        )
        if brightness_step == 0:
            return

        # Wrap action call in a task as callbacks can't be async
        asyncio.create_task(
            self._handle_light_wheel_action_task(entity_state, brightness_step)
        ).done()

    async def _handle_light_wheel_action_task(
        self, entity_state: State, brightness_step: int
    ) -> None:
        """Execute Light wheel action call."""
        _LOGGER.debug(
            "Sending %s to %s with brightness_step_pct value %s",
            SERVICE_TURN_ON,
            entity_state.entity_id,
            brightness_step,
        )
        # Suppress any exceptions for now
        with contextlib.suppress(Invalid):
            await self.hass.services.async_call(
                entity_state.domain,
                SERVICE_TURN_ON,
                {
                    ATTR_ENTITY_ID: entity_state.entity_id,
                    ATTR_BRIGHTNESS_STEP_PCT: brightness_step,
                },
            )

        # Reset counter and timer
        self._wheel_action_handlers[entity_state.entity_id].counter = 0
        self._wheel_action_handlers[entity_state.entity_id].timer = None

    def _update_connection_status(self) -> None:
        """Update all entities of the connection status."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{CONNECTION_STATUS}",
            self._client.websocket_connected,
        )

    async def on_connection(self) -> None:
        """Handle WebSocket connection made."""
        _LOGGER.debug("Connected to the %s event channel", self.entry.title)

        if self._configuration:
            # Send initial configuration
            await self._client.send(self._configuration)

            # Send entity states as updates
            for entity_id in self._entity_map.values():
                await self._update_entity_button_values(entity_id)
        else:
            _LOGGER.debug(
                "Add a configuration for Home Assistant entities to %s in config flow options",
                self.entry.title,
            )

        self._update_connection_status()

    def on_connection_lost(self) -> None:
        """Handle WebSocket connection lost."""
        _LOGGER.error("Lost connection to the %s", self.entry.title)
        self._update_connection_status()

    async def on_button_event(self, event: HaloButtonEvent) -> None:
        """Send halo_button dispatch."""
        if event.state == ButtonEventState.RELEASED:
            await self._handle_entity_button_action(event.id)

    def on_power_event(self, event: PowerEvent) -> None:
        """Send halo_power dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.HALO_POWER}",
            event,
        )

    def on_status_event(self, event: StatusEvent) -> None:
        """Send halo_status dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.HALO_STATUS}",
            event,
        )

    def on_system_event(self, event: SystemEvent) -> None:
        """Send halo_system dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.HALO_SYSTEM}",
            event,
        )

    async def on_wheel_event(self, event: WheelEvent) -> None:
        """Send halo_wheel dispatch."""

        await self._handle_entity_wheel_action(event.id, event.counts)

    def on_all_events_raw(self, event: HaloBaseWebSocketResponse) -> None:
        """Receive all events."""
        debug_event = {
            "device_id": self._device.id,
            "serial_number": int(self._unique_id),
            **event,
        }

        _LOGGER.debug("%s", debug_event)
        self.hass.bus.async_fire(HALO_WEBSOCKET_EVENT, debug_event)


class MozartWebsocket(MozartBase):
    """The WebSocket listener(s)."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: MozartClient,
    ) -> None:
        """Initialize the entity coordinator."""
        super().__init__(config_entry, client)

        self.hass = hass
        self._device = self.get_device(hass, self._unique_id)

        if TYPE_CHECKING:
            assert isinstance(self._client, MozartClient)

        # WebSocket callbacks
        self._client.get_active_listening_mode_notifications(
            self.on_active_listening_mode
        )
        self._client.get_active_speaker_group_notifications(
            self.on_active_speaker_group
        )
        self._client.get_battery_notifications(self.on_battery_notification)
        self._client.get_beo_remote_button_notifications(
            self.on_beo_remote_button_notification
        )
        self._client.get_button_notifications(self.on_button_notification)
        self._client.get_notification_notifications(self.on_notification_notification)
        self._client.get_on_connection_lost(self.on_connection_lost)
        self._client.get_on_connection(self.on_connection)
        self._client.get_playback_error_notifications(
            self.on_playback_error_notification
        )
        self._client.get_playback_metadata_notifications(
            self.on_playback_metadata_notification
        )
        self._client.get_playback_progress_notifications(
            self.on_playback_progress_notification
        )
        self._client.get_playback_source_notifications(
            self.on_playback_source_notification
        )
        self._client.get_playback_state_notifications(
            self.on_playback_state_notification
        )
        self._client.get_software_update_state_notifications(
            self.on_software_update_state
        )
        self._client.get_source_change_notifications(self.on_source_change_notification)
        self._client.get_volume_notifications(self.on_volume_notification)

        # Used for firing events and debugging
        self._client.get_all_notifications_raw(self.on_all_notifications_raw)

    def _update_connection_status(self) -> None:
        """Update all entities of the connection status."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{CONNECTION_STATUS}",
            self._client.websocket_connected,
        )

    def on_connection(self) -> None:
        """Handle WebSocket connection made."""
        _LOGGER.debug("Connected to the %s notification channel", self.entry.title)
        self._update_connection_status()

    def on_connection_lost(self) -> None:
        """Handle WebSocket connection lost."""
        _LOGGER.error("Lost connection to the %s", self.entry.title)
        self._update_connection_status()

    def on_active_listening_mode(self, notification: ListeningModeProps) -> None:
        """Send active_listening_mode dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.ACTIVE_LISTENING_MODE}",
            notification,
        )

    def on_active_speaker_group(self, notification: SpeakerGroupOverview) -> None:
        """Send active_speaker_group dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.ACTIVE_SPEAKER_GROUP}",
            notification,
        )

    def on_battery_notification(self, notification: BatteryState) -> None:
        """Send battery dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.BATTERY}",
            notification,
        )

    def on_beo_remote_button_notification(self, notification: BeoRemoteButton) -> None:
        """Send beo_remote_button dispatch."""
        if TYPE_CHECKING:
            assert notification.type

        # Send to event entity
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.BEO_REMOTE_BUTTON}_{notification.key}",
            EVENT_TRANSLATION_MAP[notification.type],
        )

    def on_button_notification(self, notification: ButtonEvent) -> None:
        """Send button dispatch."""
        assert notification.state
        # Send to event entity
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.BUTTON}_{notification.button}",
            EVENT_TRANSLATION_MAP[notification.state],
        )

    async def on_notification_notification(
        self, notification: WebsocketNotificationTag
    ) -> None:
        """Send notification dispatch."""
        assert notification.value

        # Try to match the notification type with available WebsocketNotification members
        notification_type = try_parse_enum(WebsocketNotification, notification.value)

        if notification_type in (
            WebsocketNotification.BEOLINK_PEERS,
            WebsocketNotification.BEOLINK_LISTENERS,
            WebsocketNotification.BEOLINK_AVAILABLE_LISTENERS,
        ):
            async_dispatcher_send(
                self.hass,
                f"{self._unique_id}_{WebsocketNotification.BEOLINK}",
            )
        elif notification_type is WebsocketNotification.CONFIGURATION:
            async_dispatcher_send(
                self.hass,
                f"{self._unique_id}_{WebsocketNotification.CONFIGURATION}",
            )
        elif notification_type in (
            WebsocketNotification.PROXIMITY_PRESENCE_DETECTED,
            WebsocketNotification.PROXIMITY_PRESENCE_NOT_DETECTED,
        ):
            async_dispatcher_send(
                self.hass,
                f"{self._unique_id}_{WebsocketNotification.PROXIMITY}",
                EVENT_TRANSLATION_MAP[notification.value],
            )
        # This notification is triggered by a remote pairing, unpairing and connecting to a device
        # So the current remote devices have to be compared to available remotes to determine action
        elif notification_type is WebsocketNotification.REMOTE_CONTROL_DEVICES:
            device_registry = dr.async_get(self.hass)
            device_serial_numbers = [
                device.serial_number
                for device in device_registry.devices.get_devices_for_config_entry_id(
                    self.entry.entry_id
                )
                if device.serial_number is not None
                and device.model == BangOlufsenModel.BEOREMOTE_ONE
            ]
            remote_serial_numbers = [
                remote.serial_number
                for remote in await get_remotes(self._client)
                if remote.serial_number is not None
            ]
            # Check if number of remote devices correspond to number of paired remotes
            if len(remote_serial_numbers) != len(device_serial_numbers):
                # Reinitialize the config entry to update Beoremote One entities and device
                # Wait 5 seconds for the remote to be properly available to the device
                _LOGGER.info(
                    "A Beoremote One has been paired or unpaired to %s. Reloading config entry to add device",
                    self._device.name,
                )
                self.hass.loop.call_later(
                    5,
                    self.hass.config_entries.async_schedule_reload,
                    self.entry.entry_id,
                )

        elif notification_type is WebsocketNotification.REMOTE_MENU_CHANGED:
            async_dispatcher_send(
                self.hass,
                f"{self._unique_id}_{WebsocketNotification.REMOTE_MENU_CHANGED}",
            )

    def on_playback_error_notification(self, notification: PlaybackError) -> None:
        """Send playback_error dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.PLAYBACK_ERROR}",
            notification,
        )

    def on_playback_metadata_notification(
        self, notification: PlaybackContentMetadata
    ) -> None:
        """Send playback_metadata dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.PLAYBACK_METADATA}",
            notification,
        )

    def on_playback_progress_notification(self, notification: PlaybackProgress) -> None:
        """Send playback_progress dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.PLAYBACK_PROGRESS}",
            notification,
        )

    def on_playback_source_notification(self, notification: Source) -> None:
        """Send playback_source dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.PLAYBACK_SOURCE}",
            notification,
        )

    def on_playback_state_notification(self, notification: RenderingState) -> None:
        """Send playback_state dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.PLAYBACK_STATE}",
            notification,
        )

    def on_source_change_notification(self, notification: Source) -> None:
        """Send source_change dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.SOURCE_CHANGE}",
            notification,
        )

    def on_volume_notification(self, notification: VolumeState) -> None:
        """Send volume dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.VOLUME}",
            notification,
        )

    async def on_software_update_state(self, _: SoftwareUpdateState) -> None:
        """Check device sw version."""
        software_status = await self._client.get_softwareupdate_status()

        # Update the HA device if the sw version does not match
        if software_status.software_version != self._device.sw_version:
            device_registry = dr.async_get(self.hass)

            device_registry.async_update_device(
                device_id=self._device.id,
                sw_version=software_status.software_version,
            )

    def on_all_notifications_raw(self, notification: BaseWebSocketResponse) -> None:
        """Receive all notifications."""

        _LOGGER.debug("%s", notification)
        self.hass.bus.async_fire(
            MOZART_WEBSOCKET_EVENT,
            {
                "device_id": self._device.id,
                "serial_number": int(self._unique_id),
                **notification,
            },
        )
