"""Entity representing a Bang & Olufsen device."""
from __future__ import annotations

from typing import cast

from mozart_api.models import (
    BatteryState,
    BeoRemoteButton,
    ButtonEvent,
    ListeningModeProps,
    PlaybackContentMetadata,
    PlaybackError,
    PlaybackProgress,
    PowerStateEnum,
    RenderingState,
    SoftwareUpdateState,
    SoundSettings,
    Source,
    SpeakerGroupOverview,
    VolumeLevel,
    VolumeMute,
    VolumeState,
    WebsocketNotificationTag,
)
from mozart_api.mozart_client import MozartClient

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN


class BangOlufsenBase:
    """Base class for BangOlufsen Home Assistant objects."""

    def __init__(self, entry: ConfigEntry, client: MozartClient) -> None:
        """Initialize the object."""

        # Set the MozartClient
        self._client = client

        # Get the input from the config entry.
        self.entry = entry

        # Set the configuration variables.
        self._host: str = self.entry.data[CONF_HOST]
        self._name: str = self.entry.title

        self._unique_id: str = cast(str, self.entry.unique_id)

        # Objects that get directly updated by notifications.
        self._active_listening_mode = ListeningModeProps()
        self._active_speaker_group = SpeakerGroupOverview(
            friendly_name="", id="", is_deleteable=False
        )
        self._battery: BatteryState = BatteryState()
        self._beo_remote_button: BeoRemoteButton = BeoRemoteButton()
        self._button: ButtonEvent = ButtonEvent()
        self._notification: WebsocketNotificationTag = WebsocketNotificationTag()
        self._playback_error: PlaybackError = PlaybackError()
        self._playback_metadata: PlaybackContentMetadata = PlaybackContentMetadata()
        self._playback_progress: PlaybackProgress = PlaybackProgress(total_duration=0)
        self._playback_source: Source = Source()
        self._playback_state: RenderingState = RenderingState()
        self._power_state: PowerStateEnum = PowerStateEnum()
        self._software_update_state: SoftwareUpdateState = SoftwareUpdateState()
        self._sound_settings: SoundSettings = SoundSettings()
        self._source_change: Source = Source()
        self._volume: VolumeState = VolumeState(
            level=VolumeLevel(level=0), muted=VolumeMute(muted=False)
        )


class BangOlufsenEntity(Entity, BangOlufsenBase):
    """Base Entity for BangOlufsen entities."""

    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, client: MozartClient) -> None:
        """Initialize the object."""
        super().__init__(entry, client)

        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, self._unique_id)})
        self._attr_device_class = None
        self._attr_entity_category = None
        self._attr_should_poll = False

    async def _update_connection_state(self, connection_state: bool) -> None:
        """Update entity connection state."""
        self._attr_available = connection_state

        self.async_write_ha_state()

    def set_entity_initialized(self):
        """Increment number of initialized entities."""
        self.hass.data[DOMAIN][self.entry.entry_id].entities_initialized += 1
