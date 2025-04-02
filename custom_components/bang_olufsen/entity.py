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
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .beoremote_halo.halo import Halo
from .const import DOMAIN


class BangOlufsenBase:
    """Base class for Bang & Olufsen Home Assistant objects."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the object."""

        # Get the input from the config entry.
        self.entry = config_entry

        # Set the configuration variables.
        self._host: str = self.entry.data[CONF_HOST]
        self._unique_id: str = cast(str, self.entry.unique_id)

    @staticmethod
    def get_device(hass: HomeAssistant, unique_id: str) -> dr.DeviceEntry:
        """Get the device."""
        device_registry = dr.async_get(hass)
        device = device_registry.async_get_device({(DOMAIN, unique_id)})
        assert device

        return device


class MozartBase(BangOlufsenBase):
    """Base class for Mozart."""

    def __init__(
        self, config_entry: ConfigEntry, client: MozartClient | None = None
    ) -> None:
        """Initialize Mozart specific variables."""
        super().__init__(config_entry)

        # Set the Mozart client.
        # Allowing the client to be set directly allows the coordinator to be initialized before being added to runtime_data.
        if client:
            self._client = client
        else:
            self._client = config_entry.runtime_data.client

        # Objects that get directly updated by Mozart notifications.
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


class MozartEntity(Entity, MozartBase):
    """Base Entity for Bang & Olufsen Mozart entities."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the object."""
        super().__init__(config_entry)

        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, self._unique_id)})

    @callback
    def _async_update_connection_state(self, connection_state: bool) -> None:
        """Update entity connection state."""
        self._attr_available = connection_state

        self.async_write_ha_state()


class HaloBase(BangOlufsenBase):
    """Base class for Halo."""

    def __init__(self, config_entry: ConfigEntry, client: Halo | None = None) -> None:
        """Initialize Halo specific variables."""
        super().__init__(config_entry)

        # Set the Halo client.
        # Allowing the client to be set directly allows the coordinator to be initialized before being added to runtime_data.
        if client:
            self._client = client
        else:
            self._client = config_entry.runtime_data.client


class HaloEntity(Entity, HaloBase):
    """Base Entity for Bang & Olufsen Halo entities."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the object."""
        super().__init__(config_entry)

        self._attr_device_info = DeviceInfo(
            configuration_url=f"http://{self._host}:8080",
            identifiers={(DOMAIN, self._unique_id)},
        )

    @callback
    def _async_update_connection_state(self, connection_state: bool) -> None:
        """Update entity connection state."""
        self._attr_available = connection_state

        self.async_write_ha_state()
