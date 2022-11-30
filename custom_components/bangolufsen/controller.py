"""Websocket listener handling for the Bang & Olufsen integration."""
from __future__ import annotations

import asyncio
import logging

from mozart_api.models import (
    BatteryState,
    BeoRemoteButton,
    ButtonEvent,
    PlaybackContentMetadata,
    PlaybackError,
    PlaybackProgress,
    RenderingState,
    SoundSettings,
    Source,
    VolumeState,
    WebsocketNotificationTag,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_ID, CONF_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)

from .const import (
    BANGOLUFSEN_EVENT,
    BANGOLUFSEN_WEBSOCKET_EVENT,
    CLEANUP,
    CONNECTION_STATUS,
    WS_REMOTE_CONTROL_AVAILABLE,
    BangOlufsenVariables,
    WebSocketNotification,
    get_device,
)

_LOGGER = logging.getLogger(__name__)


class BangOlufsenController(BangOlufsenVariables):
    """The dispatcher and handler for WebSocket notifications."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Init the dispatcher and handler for WebSocket notifications."""
        super().__init__(entry)

        self.hass = hass
        self.websocket_remote_control: bool = False

        # Get the device for device triggers
        self._device: DeviceEntry | None = get_device(self.hass, self._unique_id)

        self._client.get_on_connection(self.on_connection)
        self._client.get_on_connection_lost(self.on_connection_lost)
        self._client.get_battery_notifications(self.on_battery_notification)
        self._client.get_beo_remote_button_notifications(
            self.on_beo_remote_button_notification
        )
        self._client.get_button_notifications(self.on_button_notification)
        self._client.get_notification_notifications(self.on_notification_notification)
        self._client.get_playback_error_notifications(
            self.on_playback_error_notification
        )
        self._client.get_playback_metadata_notifications(
            self.on_playback_metadata_notification
        )
        self._client.get_playback_progress_notifications(
            self.on_playback_progress_notification
        )
        self._client.get_playback_state_notifications(
            self.on_playback_state_notification
        )
        self._client.get_sound_settings_notifications(
            self.on_sound_settings_notification
        )
        self._client.get_source_change_notifications(self.on_source_change_notification)
        self._client.get_volume_notifications(self.on_volume_notification)

        # Used for firing events and debugging
        self._client.get_all_notifications_raw(self.on_all_notifications_raw)

        # Register dispatchers.
        self._dispatchers = [
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{CLEANUP}",
                self._disconnect,
            ),
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{WS_REMOTE_CONTROL_AVAILABLE}",
                self.start_notification_listener,
            ),
        ]

    async def start_notification_listener(self) -> bool:
        """Start the notification WebSocket listener."""

        # Kill notification listeners if already running
        if self._client.websocket_connected:
            self._client.disconnect_notifications()

        # Check if the remote control listener should be activated.
        bluetooth_remote_list = self._client.get_bluetooth_remotes(async_req=True).get()

        if len(bluetooth_remote_list.items) > 0:
            self.websocket_remote_control = True

        status = await self._async_receive_notifications()
        return status

    async def _disconnect(self) -> None:
        """Terminate the WebSocket connection(s) and remove dispatchers."""
        await self._wait_for_disconnect()
        self._update_connection_status()

        for dispatcher in self._dispatchers:
            dispatcher()

    def _update_connection_status(self) -> None:
        """Update all entities of the connection status."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{CONNECTION_STATUS}",
            self._client.websocket_connected,
        )

    async def _wait_for_connection(self) -> None:
        """Wait for WebSocket connection to be established."""
        self._client.connect_notifications(self.websocket_remote_control)

        while not self._client.websocket_connected:
            pass

    async def _wait_for_disconnect(self) -> None:
        """Wait for WebSocket connection to be disconnected."""
        self._client.disconnect_notifications()

        while self._client.websocket_connected:
            pass

    async def _async_receive_notifications(self) -> bool:
        """Receive all WebSocket notifications."""
        try:
            await asyncio.wait_for(self._wait_for_connection(), timeout=10.0)
        except asyncio.TimeoutError:
            _LOGGER.error("Unable to connect to the WebSocket notification channel")
            return False
        return True

    def on_connection(self) -> None:
        """Handle WebSocket connection made."""
        _LOGGER.info("Connected to the %s notification channel", self._name)
        self._update_connection_status()

    def on_connection_lost(self) -> None:
        """Handle WebSocket connection lost."""
        _LOGGER.error("Lost connection to the %s", self._name)
        self._update_connection_status()

    def on_battery_notification(self, notification: BatteryState) -> None:
        """Send battery dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebSocketNotification.BATTERY}",
            notification,
        )

    def on_beo_remote_button_notification(self, notification: BeoRemoteButton) -> None:
        """Send beo_remote_button dispatch."""
        if not isinstance(self._device, DeviceEntry):
            self._device = get_device(self.hass, self._unique_id)

        assert isinstance(self._device, DeviceEntry)

        if notification.type == "KeyPress":
            self.hass.bus.async_fire(
                BANGOLUFSEN_EVENT,
                event_data={
                    CONF_TYPE: f"{notification.key}_{notification.type}",
                    CONF_DEVICE_ID: self._device.id,
                },
            )

    def on_button_notification(self, notification: ButtonEvent) -> None:
        """Send button dispatch."""
        if not isinstance(self._device, DeviceEntry):
            self._device = get_device(self.hass, self._unique_id)

        assert isinstance(self._device, DeviceEntry)

        # Trigger the device trigger
        self.hass.bus.async_fire(
            BANGOLUFSEN_EVENT,
            event_data={
                CONF_TYPE: f"{notification.button}_{notification.state}",
                CONF_DEVICE_ID: self._device.id,
            },
        )

    def on_notification_notification(
        self, notification: WebsocketNotificationTag
    ) -> None:
        """Send notification dispatch."""

        if "proximity" in notification.value:
            async_dispatcher_send(
                self.hass,
                f"{self._unique_id}_{WebSocketNotification.PROXIMITY}",
                notification,
            )
        else:
            async_dispatcher_send(
                self.hass,
                f"{self._unique_id}_{WebSocketNotification.NOTIFICATION}",
                notification,
            )

    def on_playback_error_notification(self, notification: PlaybackError) -> None:
        """Send playback_error dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebSocketNotification.PLAYBACK_ERROR}",
            notification,
        )

    def on_playback_metadata_notification(
        self, notification: PlaybackContentMetadata
    ) -> None:
        """Send playback_metadata dispatch."""

        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebSocketNotification.PLAYBACK_METADATA}",
            notification,
        )

    def on_playback_progress_notification(self, notification: PlaybackProgress) -> None:
        """Send playback_progress dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebSocketNotification.PLAYBACK_PROGRESS}",
            notification,
        )

    def on_playback_state_notification(self, notification: RenderingState) -> None:
        """Send playback_state dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebSocketNotification.PLAYBACK_STATE}",
            notification,
        )

    def on_sound_settings_notification(self, notification: SoundSettings) -> None:
        """Send sound_settings dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebSocketNotification.SOUND_SETTINGS}",
            notification,
        )

    def on_source_change_notification(self, notification: Source) -> None:
        """Send source_change dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebSocketNotification.SOURCE_CHANGE}",
            notification,
        )

    def on_volume_notification(self, notification: VolumeState) -> None:
        """Send volume dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebSocketNotification.VOLUME}",
            notification,
        )

    def on_all_notifications_raw(self, notification: dict) -> None:
        """Receive all notifications."""
        _LOGGER.debug("%s : %s", self._name, notification)
        self.hass.bus.async_fire(BANGOLUFSEN_WEBSOCKET_EVENT, notification)
