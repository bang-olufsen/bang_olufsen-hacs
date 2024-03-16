"""Update coordinator and WebSocket listener(s) for the Bang & Olufsen integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging

from aiohttp.client_exceptions import ClientConnectorError
from mozart_api.exceptions import ApiException
from mozart_api.models import (
    BatteryState,
    BeoRemoteButton,
    ButtonEvent,
    ListeningModeProps,
    PlaybackContentMetadata,
    PlaybackError,
    PlaybackProgress,
    PlayQueueSettings,
    Preset,
    RenderingState,
    SoftwareUpdateState,
    SoundSettings,
    Source,
    SpeakerGroupOverview,
    VolumeState,
    WebsocketNotificationTag,
)
from mozart_api.mozart_client import MozartClient

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_ID, CONF_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    BANG_OLUFSEN_EVENT,
    BANG_OLUFSEN_WEBSOCKET_EVENT,
    CONNECTION_STATUS,
    DOMAIN,
    WebsocketNotification,
)
from .entity import BangOlufsenBase

_LOGGER = logging.getLogger(__name__)


@dataclass
class CoordinatorData:
    """Dataclass for coordinator data."""

    favourites: dict[str, Preset]
    queue_settings: PlayQueueSettings


class BangOlufsenCoordinator(DataUpdateCoordinator, BangOlufsenBase):
    """The entity coordinator and WebSocket listener(s)."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: MozartClient
    ) -> None:
        """Initialize the entity coordinator."""
        DataUpdateCoordinator.__init__(
            self,
            hass,
            _LOGGER,
            name="coordinator",
            update_interval=timedelta(seconds=15),
            always_update=False,
        )
        BangOlufsenBase.__init__(self, entry, client)

        self._coordinator_data: CoordinatorData = CoordinatorData(
            favourites={},
            queue_settings=PlayQueueSettings(),
        )

        self._device = self._get_device()

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
        self._client.get_playback_state_notifications(
            self.on_playback_state_notification
        )
        self._client.get_software_update_state_notifications(
            self.on_software_update_state
        )
        self._client.get_sound_settings_notifications(
            self.on_sound_settings_notification
        )
        self._client.get_source_change_notifications(self.on_source_change_notification)
        self._client.get_volume_notifications(self.on_volume_notification)

        # Used for firing events and debugging
        self._client.get_all_notifications_raw(self.on_all_notifications_raw)

    async def _update_variables(self) -> None:
        """Update the coordinator data."""
        favourites = await self._client.get_presets(_request_timeout=5)
        queue_settings = await self._client.get_settings_queue(_request_timeout=5)

        self._coordinator_data = CoordinatorData(
            favourites=favourites,
            queue_settings=queue_settings,
        )

    async def _async_update_data(self) -> CoordinatorData:
        """Get all information needed by the polling entities."""
        # Try to update coordinator_data.
        try:
            await self._update_variables()
            return self._coordinator_data

        except (TimeoutError, ClientConnectorError, ApiException) as error:
            raise UpdateFailed from error

    def _update_connection_status(self) -> None:
        """Update all entities of the connection status."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{CONNECTION_STATUS}",
            self._client.websocket_connected,
        )

    def _get_device(self) -> DeviceEntry | None:
        """Get the Home Assistant device."""
        if not self.hass:
            return None

        device_registry = dr.async_get(self.hass)
        device = device_registry.async_get_device({(DOMAIN, self._unique_id)})
        assert device

        return device

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
        if not self._device:
            self._device = self._get_device()

        assert self._device

        if notification.type == "KeyPress":
            # Trigger the device trigger
            self.hass.bus.async_fire(
                BANG_OLUFSEN_EVENT,
                event_data={
                    CONF_TYPE: f"{notification.key}_{notification.type}",
                    CONF_DEVICE_ID: self._device.id,
                },
            )

    def on_button_notification(self, notification: ButtonEvent) -> None:
        """Send button dispatch."""
        if not self._device:
            self._device = self._get_device()

        assert self._device

        # Trigger the device trigger
        self.hass.bus.async_fire(
            BANG_OLUFSEN_EVENT,
            event_data={
                CONF_TYPE: f"{notification.button}_{notification.state}",
                CONF_DEVICE_ID: self._device.id,
            },
        )

    def on_notification_notification(
        self, notification: WebsocketNotificationTag
    ) -> None:
        """Send notification dispatch."""
        if notification.value:
            if notification.value is WebsocketNotification.PROXIMITY:
                async_dispatcher_send(
                    self.hass,
                    f"{self._unique_id}_{WebsocketNotification.PROXIMITY}",
                    notification,
                )

            elif notification.value is WebsocketNotification.REMOTE_MENU_CHANGED.value:
                async_dispatcher_send(
                    self.hass,
                    f"{self._unique_id}_{WebsocketNotification.REMOTE_MENU_CHANGED}",
                )

            elif notification.value is WebsocketNotification.CONFIGURATION.value:
                async_dispatcher_send(
                    self.hass,
                    f"{self._unique_id}_{WebsocketNotification.CONFIGURATION}",
                )

            elif notification.value in (
                WebsocketNotification.BLUETOOTH_DEVICES.value,
                WebsocketNotification.REMOTE_CONTROL_DEVICES.value,
            ):
                async_dispatcher_send(
                    self.hass,
                    f"{self._unique_id}_{WebsocketNotification.BLUETOOTH_DEVICES}",
                )
            elif WebsocketNotification.BEOLINK.value in notification.value:
                async_dispatcher_send(
                    self.hass,
                    f"{self._unique_id}_{WebsocketNotification.BEOLINK}",
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

    def on_playback_state_notification(self, notification: RenderingState) -> None:
        """Send playback_state dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.PLAYBACK_STATE}",
            notification,
        )

    def on_sound_settings_notification(self, notification: SoundSettings) -> None:
        """Send sound_settings dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.SOUND_SETTINGS}",
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
        if not self._device:
            self._device = self._get_device()

        assert self._device

        if software_status.software_version != self._device.sw_version:
            device_registry = dr.async_get(self.hass)

            device_registry.async_update_device(
                device_id=self._device.id,
                sw_version=software_status.software_version,
            )

    def on_all_notifications_raw(self, notification: dict) -> None:
        """Receive all notifications."""
        if not self._device:
            self._device = self._get_device()

        assert self._device

        # Add the device_id and serial_number to the notification
        notification["device_id"] = self._device.id
        notification["serial_number"] = int(self._unique_id)

        _LOGGER.warning("%s", notification)
        self.hass.bus.async_fire(BANG_OLUFSEN_WEBSOCKET_EVENT, notification)
