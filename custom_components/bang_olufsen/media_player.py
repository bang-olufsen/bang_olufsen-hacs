"""Media player entity for the Bang & Olufsen integration."""

from __future__ import annotations

from collections.abc import Callable
import contextlib
from datetime import timedelta
import json
import logging
from typing import TYPE_CHECKING, Any, cast

from aiohttp import ClientConnectorError
from inflection import titleize, underscore
from mozart_api.exceptions import ApiException
from mozart_api.models import (
    Action,
    Art,
    BeolinkLeader,
    BeolinkListener,
    ListeningModeProps,
    ListeningModeRef,
    OverlayPlayRequest,
    OverlayPlayRequestTextToSpeechTextToSpeech,
    PlaybackContentMetadata,
    PlaybackError,
    PlaybackProgress,
    PlayQueueItem,
    PlayQueueItemType,
    PlayQueueSettings,
    Preset,
    RenderingState,
    SceneProperties,
    SoftwareUpdateState,
    SoftwareUpdateStatus,
    Source,
    Uri,
    UserFlow,
    VolumeLevel,
    VolumeMute,
    VolumeState,
)
from mozart_api.mozart_client import get_highest_resolution_artwork
import voluptuous as vol

from homeassistant.components import media_source
from homeassistant.components.media_player import (
    ATTR_MEDIA_EXTRA,
    BrowseMedia,
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    RepeatMode,
    async_process_play_media_url,
)
from homeassistant.const import CONF_MODEL, Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.device_registry import DeviceEntry, DeviceInfo
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
    async_get_current_platform,
)
from homeassistant.util.dt import utcnow
from homeassistant.util.json import JsonObjectType

from . import MANUFACTURER, MozartConfigEntry
from .const import (
    ACCEPTED_COMMANDS,
    ACCEPTED_COMMANDS_LISTS,
    BANG_OLUFSEN_REPEAT_FROM_HA,
    BANG_OLUFSEN_REPEAT_TO_HA,
    BANG_OLUFSEN_STATES,
    BEOLINK_JOIN_SOURCES,
    BEOLINK_JOIN_SOURCES_TO_UPPER,
    BEOLINK_LEADER_COMMAND,
    BEOLINK_LISTENER_COMMAND,
    BEOLINK_RELATIVE_VOLUME,
    BEOLINK_VOLUME,
    CONF_BEOLINK_JID,
    CONNECTION_STATUS,
    DOMAIN,
    VALID_MEDIA_TYPES,
    BangOlufsenMediaType,
    BangOlufsenSource,
    WebsocketNotification,
)
from .entity import MozartEntity
from .util import get_serial_number_from_jid, get_sources

PARALLEL_UPDATES = 0

SCAN_INTERVAL = timedelta(seconds=30)

_LOGGER = logging.getLogger(__name__)

BANG_OLUFSEN_FEATURES = (
    MediaPlayerEntityFeature.BROWSE_MEDIA
    | MediaPlayerEntityFeature.CLEAR_PLAYLIST
    | MediaPlayerEntityFeature.GROUPING
    | MediaPlayerEntityFeature.MEDIA_ANNOUNCE
    | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.PLAY_MEDIA
    | MediaPlayerEntityFeature.PREVIOUS_TRACK
    | MediaPlayerEntityFeature.REPEAT_SET
    | MediaPlayerEntityFeature.SEEK
    | MediaPlayerEntityFeature.SELECT_SOUND_MODE
    | MediaPlayerEntityFeature.SELECT_SOURCE
    | MediaPlayerEntityFeature.SHUFFLE_SET
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.VOLUME_SET
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: MozartConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up a Media Player entity from config entry."""
    entities: list[MozartMediaPlayer] = []

    entities.append(MozartMediaPlayer(config_entry))

    async_add_entities(new_entities=entities, update_before_add=True)

    # Register services.
    platform = async_get_current_platform()

    jid_regex = vol.Match(
        r"(^\d{4})[.](\d{7})[.](\d{8})(@products\.bang-olufsen\.com)$"
    )

    platform.async_register_entity_service(
        name="beolink_join",
        schema={
            vol.Optional("beolink_jid"): jid_regex,
            vol.Optional("source_id"): vol.In(BEOLINK_JOIN_SOURCES),
        },
        func="async_beolink_join",
        supports_response=SupportsResponse.OPTIONAL,
    )

    platform.async_register_entity_service(
        name="beolink_expand",
        schema={
            vol.Exclusive("all_discovered", "devices", ""): cv.boolean,
            vol.Exclusive(
                "beolink_jids",
                "devices",
                "Define either specific Beolink JIDs or all discovered",
            ): vol.All(
                cv.ensure_list,
                [jid_regex],
            ),
        },
        func="async_beolink_expand",
        supports_response=SupportsResponse.OPTIONAL,
    )

    platform.async_register_entity_service(
        name="beolink_unexpand",
        schema={
            vol.Required("beolink_jids"): vol.All(
                cv.ensure_list,
                [jid_regex],
            ),
        },
        func="async_beolink_unexpand",
    )

    platform.async_register_entity_service(
        name="beolink_leave",
        schema=None,
        func="async_beolink_leave",
    )

    platform.async_register_entity_service(
        name="beolink_allstandby",
        schema=None,
        func="async_beolink_allstandby",
    )

    platform.async_register_entity_service(
        name="beolink_set_volume",
        schema={vol.Required("volume_level"): cv.string},
        func="async_beolink_set_volume",
    )

    platform.async_register_entity_service(
        name="beolink_set_relative_volume",
        schema={vol.Required("volume_level"): cv.string},
        func="async_beolink_set_relative_volume",
    )

    platform.async_register_entity_service(
        name="beolink_leader_command",
        schema={
            vol.Required("command"): vol.In(ACCEPTED_COMMANDS),
            vol.Optional("parameter"): cv.string,
        },
        func="async_beolink_leader_command",
    )

    platform.async_register_entity_service(
        name="reboot",
        schema=None,
        func="async_reboot",
    )


class MozartMediaPlayer(MediaPlayerEntity, MozartEntity):
    """Representation of a media player."""

    _attr_device_class = MediaPlayerDeviceClass.SPEAKER
    _attr_name: None | str = None

    def __init__(self, config_entry: MozartConfigEntry) -> None:
        """Initialize the media player."""
        super().__init__(config_entry)

        self._beolink_jid: str = self.entry.data[CONF_BEOLINK_JID]
        self._model: str = self.entry.data[CONF_MODEL]

        self._attr_device_info = DeviceInfo(
            configuration_url=f"http://{self._host}/#/",
            identifiers={(DOMAIN, self._unique_id)},
            manufacturer=MANUFACTURER,
            model=self._model,
            serial_number=self._unique_id,
        )
        self._attr_unique_id = self._unique_id
        self._attr_should_poll = True

        # Misc. variables.
        self._audio_sources: dict[str, str] = {}
        self._media_image = Art()
        self._software_status = SoftwareUpdateStatus(
            software_version="",
            state=SoftwareUpdateState(seconds_remaining=0, value="idle"),
        )
        self._sources: dict[str, str] = {}
        self._state: str = MediaPlayerState.IDLE
        self._video_sources: dict[str, str] = {}
        self._sound_modes: dict[str, int] = {}
        self._unsorted_sources: dict[str, str] = {}

        # Beolink
        self._beolink_sources: dict[str, bool] = {}
        self._remote_leader: BeolinkLeader | None = None
        self._beolink_listeners: list[BeolinkListener] = []

        # Extra state attributes
        self._beolink_attributes: dict[str, dict[str, Any]] = {}
        self._favourite_attribute: dict[str, dict[str, Any]] = {}
        self._input_signal_attribute: str | None = None
        self._media_id_attribute: str | None = None

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        await super().async_added_to_hass()

        await self._initialize()

        signal_handler_map: dict[str, dict[str, Callable]] = {
            self._beolink_jid: {
                BEOLINK_LEADER_COMMAND: self.async_beolink_leader_command,
                BEOLINK_LISTENER_COMMAND: self.async_beolink_listener_command,
                BEOLINK_RELATIVE_VOLUME: self.async_beolink_set_relative_volume,
                BEOLINK_VOLUME: self.async_beolink_set_volume,
            },
            self._unique_id: {
                CONNECTION_STATUS: self._async_update_connection_state,
                WebsocketNotification.ACTIVE_LISTENING_MODE: self._async_update_sound_modes,
                WebsocketNotification.BEOLINK: self._async_update_beolink,
                WebsocketNotification.CONFIGURATION: self._async_update_name_and_beolink,
                WebsocketNotification.PLAYBACK_ERROR: self._async_update_playback_error,
                WebsocketNotification.PLAYBACK_METADATA: self._async_update_playback_metadata_and_beolink,
                WebsocketNotification.PLAYBACK_PROGRESS: self._async_update_playback_progress,
                WebsocketNotification.PLAYBACK_SOURCE: self._async_update_sources,
                WebsocketNotification.PLAYBACK_STATE: self._async_update_playback_state,
                WebsocketNotification.REMOTE_MENU_CHANGED: self._async_update_sources,
                WebsocketNotification.SOURCE_CHANGE: self._async_update_source_change,
                WebsocketNotification.VOLUME: self._async_update_volume,
            },
        }

        for signal_prefix, signal_handlers in signal_handler_map.items():
            for signal, signal_handler in signal_handlers.items():
                self.async_on_remove(
                    async_dispatcher_connect(
                        self.hass,
                        f"{signal_prefix}_{signal}",
                        signal_handler,
                    )
                )

    async def _initialize(self) -> None:
        """Initialize connection dependent variables."""

        # Get software version.
        self._software_status = await self._client.get_softwareupdate_status()

        _LOGGER.debug(
            "Connected to: %s %s running SW %s",
            self._model,
            self._unique_id,
            self._software_status.software_version,
        )

        self._attr_media_position_updated_at = utcnow()

        # Get the highest resolution available of the given images.
        self._media_image = get_highest_resolution_artwork(self._playback_metadata)

        # If the device has been updated with new sources, then the API will fail here.
        await self._async_update_sources()

        await self._async_update_sound_modes()

        # Update beolink attributes and device name.
        await self._async_update_name_and_beolink()

    async def async_update(self) -> None:
        """Update queue settings."""
        # The WebSocket event listener is the main handler for connection state.
        # The polling updates do therefore not set the device as available or unavailable
        with contextlib.suppress(ApiException, ClientConnectorError, TimeoutError):
            favourites = await self._client.get_presets(_request_timeout=5)
            await self._generate_favourite_attributes(favourites)

            queue_settings = await self._client.get_settings_queue(_request_timeout=5)
            if queue_settings.repeat is not None:
                self._attr_repeat = BANG_OLUFSEN_REPEAT_TO_HA[queue_settings.repeat]

            if queue_settings.shuffle is not None:
                self._attr_shuffle = queue_settings.shuffle

    async def _generate_favourite_attributes(
        self, favourites: dict[str, Preset]
    ) -> None:
        """Generate extra state attributes for favourites."""
        # As this is run before sources are defined, unsorted sources are found once here
        if not self._unsorted_sources:
            sources = await get_sources(self._client)

            # Store the ids and Friendly names of all sources to use in favourites attributes
            self._unsorted_sources = {
                source.id: source.name
                for source in sources
                if source.id and source.name
            }

        self._favourite_attribute = {"favourites": {}}

        # Handle each favourite
        for favourite_id, favourite in favourites.items():
            favourite_attribute = {"title": favourite.title}

            # Handle each action
            for action in cast(list[Action], favourite.action_list):
                # Add source
                source = ""

                if action.source and action.source.value:
                    source = action.source.value

                elif action.queue_item:
                    source = action.queue_item.provider.value

                # Add friendly name if it has been defined
                if source:
                    favourite_attribute["source"] = self._unsorted_sources[source]

                # Add content id if available
                content_id = ""
                if action.content_id:
                    # Determine if a netradio id should be split
                    if "netRadio" in action.content_id:
                        content_id = action.content_id.split("netRadio://")[1]
                elif action.queue_item:
                    # Determine if a netradio id should be split
                    if "tidal" in action.queue_item.uri:
                        content_id = action.queue_item.uri.split("tidal://")[1]
                    else:
                        content_id = action.queue_item.uri
                elif action.deezer_user_id:
                    content_id = action.deezer_user_id

                # Add content id if it has been defined
                if content_id:
                    favourite_attribute["content_id"] = content_id

            # Check content for source if it hasn't been defined in actionlist
            if "source" not in favourite_attribute:
                if favourite.content and favourite.content.source.value:
                    favourite_attribute["source"] = self._unsorted_sources[
                        favourite.content.source.value
                    ]

            # Add current favourite to attribute
            self._favourite_attribute["favourites"][favourite_id] = favourite_attribute

    async def _async_update_sources(self, _: Source | None = None) -> None:
        """Get sources for the specific product."""
        # Audio sources
        sources = await get_sources(self._client)

        # Save all of the relevant enabled sources, both the ID and the friendly name for displaying in a dict.
        self._audio_sources = {
            source.id: source.name
            for source in sources
            if source.is_enabled and source.id and source.name and source.is_playable
        }

        # Some sources are not Beolink expandable, meaning that they can't be joined by or expand to other Bang & Olufsen devices for a multi-room experience.
        # _source_change, which is used throughout the entity for current source information, lacks this information,
        # so source ID's and their expandability is stored in the self._beolink_sources variable.
        self._beolink_sources = {
            source.id: (
                source.is_multiroom_available
                if source.is_multiroom_available is not None
                else False
            )
            for source in sources
            if source.id
        }

        # Video sources from remote menu
        menu_items = await self._client.get_remote_menu()

        for key in menu_items:
            menu_item = menu_items[key]

            if not menu_item.available:
                continue

            # TV SOURCES
            if (
                menu_item.content is not None
                and menu_item.content.categories
                and len(menu_item.content.categories) > 0
                and "music" not in menu_item.content.categories
                and menu_item.label
                and menu_item.label != "TV"
            ):
                self._video_sources[key] = menu_item.label

        # Combine the source dicts
        self._sources = self._audio_sources | self._video_sources

        self._attr_source_list = list(self._sources.values())

        self.async_write_ha_state()

    async def _async_update_playback_metadata_and_beolink(
        self, data: PlaybackContentMetadata
    ) -> None:
        """Update _playback_metadata and related."""
        self._playback_metadata = data

        # Update current artwork and remote_leader.
        self._media_image = get_highest_resolution_artwork(self._playback_metadata)
        await self._async_update_beolink()

        # Update media id attribute
        self._media_id_attribute = data.source_internal_id

        # Update input signal attribute
        if data.encoding:
            # Ensure that abbreviated formats are capitialized and non-abbreviated formats are made "human readable"
            encoding = titleize(underscore(data.encoding))
            if data.encoding.capitalize() == encoding:
                encoding = data.encoding.upper()

            input_channel_processing = None
            if data.input_channel_processing:
                input_channel_processing = titleize(
                    underscore(data.input_channel_processing)
                )

            self._input_signal_attribute = f"{encoding}{f' - {input_channel_processing}' if input_channel_processing else ''}{f' - {data.input_channels}' if data.input_channels else ''}"
        else:
            self._input_signal_attribute = None

    @callback
    def _async_update_playback_error(self, data: PlaybackError) -> None:
        """Show playback error."""
        raise HomeAssistantError(data.error)

    @callback
    def _async_update_playback_progress(self, data: PlaybackProgress) -> None:
        """Update _playback_progress and last update."""
        self._playback_progress = data
        self._attr_media_position_updated_at = utcnow()

        self.async_write_ha_state()

    @callback
    def _async_update_playback_state(self, data: RenderingState) -> None:
        """Update _playback_state and related."""
        self._playback_state = data

        # Update entity state based on the playback state.
        if self._playback_state.value:
            self._state = self._playback_state.value

            self.async_write_ha_state()

    async def _async_update_source_change(self, data: Source) -> None:
        """Update _source_change and related."""
        self._source_change = data

        # Check if source is line-in or optical and progress should be updated
        if self._source_change.id in (
            BangOlufsenSource.LINE_IN.id,
            BangOlufsenSource.SPDIF.id,
        ):
            self._playback_progress = PlaybackProgress(progress=0)

        # Try to ensure that a source is active (not unknown).
        elif self._source_change.id == BangOlufsenSource.UNKNOWN.id:
            sources = await get_sources(self._client)

            default_source = None

            # Get USB or Line-in, depending on which one of them is enabled
            for source in sources:
                if source.is_enabled and source.id in (
                    BangOlufsenSource.LINE_IN.id,
                    BangOlufsenSource.USB_IN.id,
                ):
                    default_source = source.id
                    break

            # Set either USB or Line-in as the active source
            if default_source:
                await self._client.set_active_source(source_id=default_source)

            _LOGGER.debug(
                "No current source%s",
                f". Defaulting to {default_source}" if default_source else "",
            )

        self.async_write_ha_state()

    @callback
    def _async_update_volume(self, data: VolumeState) -> None:
        """Update _volume."""
        self._volume = data

        self.async_write_ha_state()

    async def _async_update_name_and_beolink(self) -> None:
        """Update the device friendly name."""
        beolink_self = await self._client.get_beolink_self()

        # Update device name
        device_registry = dr.async_get(self.hass)
        device_registry.async_update_device(
            device_id=cast(DeviceEntry, self.device_entry).id,
            name=beolink_self.friendly_name,
        )

        await self._async_update_beolink()

    async def _async_update_beolink(self) -> None:
        """Update the current Beolink leader, listeners, peers and self."""

        self._beolink_attributes = {}

        assert self.device_entry

        # Add Beolink self
        self._beolink_attributes = {
            "beolink": {"self": {self.device_entry.name: self._beolink_jid}}
        }

        # Add Beolink peers
        peers = await self._client.get_beolink_peers()

        if len(peers) > 0:
            self._beolink_attributes["beolink"]["peers"] = {}
            for peer in peers:
                self._beolink_attributes["beolink"]["peers"][peer.friendly_name] = (
                    peer.jid
                )

        # Add Beolink listeners / leader
        self._remote_leader = self._playback_metadata.remote_leader

        # Create group members list
        group_members = []

        # If the device is a listener.
        if self._remote_leader is not None:
            # Add leader if available in Home Assistant
            leader = self._get_entity_id_from_jid(self._remote_leader.jid)
            group_members.append(
                leader
                if leader is not None
                else f"leader_not_in_hass-{self._remote_leader.friendly_name}"
            )

            # Add self
            group_members.append(self.entity_id)

            self._beolink_attributes["beolink"]["leader"] = {
                self._remote_leader.friendly_name: self._remote_leader.jid,
            }

        # If not listener, check if leader.
        else:
            self._beolink_listeners = await self._client.get_beolink_listeners()
            beolink_listeners_attribute = {}

            # Check if the device is a leader.
            if len(self._beolink_listeners) > 0:
                # Add self
                group_members.append(self.entity_id)

                # Get the entity_ids of the listeners if available in Home Assistant
                group_members.extend(
                    [
                        listener
                        if (
                            listener := self._get_entity_id_from_jid(
                                beolink_listener.jid
                            )
                        )
                        is not None
                        else f"listener_not_in_hass-{beolink_listener.jid}"
                        for beolink_listener in self._beolink_listeners
                    ]
                )
                # Update Beolink attributes
                for beolink_listener in self._beolink_listeners:
                    for peer in peers:
                        if peer.jid == beolink_listener.jid:
                            # Get the friendly names for the listeners from the peers
                            beolink_listeners_attribute[peer.friendly_name] = (
                                beolink_listener.jid
                            )
                            break
                self._beolink_attributes["beolink"]["listeners"] = (
                    beolink_listeners_attribute
                )

        self._attr_group_members = group_members

        self.async_write_ha_state()

    def _get_entity_id_from_jid(self, jid: str) -> str | None:
        """Get entity_id from Beolink JID (if available)."""

        unique_id = get_serial_number_from_jid(jid)

        entity_registry = er.async_get(self.hass)
        return entity_registry.async_get_entity_id(
            Platform.MEDIA_PLAYER, DOMAIN, unique_id
        )

    def _get_beolink_jid(self, entity_id: str) -> str:
        """Get beolink JID from entity_id."""

        entity_registry = er.async_get(self.hass)

        # Check for valid bang_olufsen media_player entity
        entity_entry = entity_registry.async_get(entity_id)

        if (
            entity_entry is None
            or entity_entry.domain != Platform.MEDIA_PLAYER
            or entity_entry.platform != DOMAIN
            or entity_entry.config_entry_id is None
        ):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_grouping_entity",
                translation_placeholders={"entity_id": entity_id},
            )

        config_entry = self.hass.config_entries.async_get_entry(
            entity_entry.config_entry_id
        )
        if TYPE_CHECKING:
            assert config_entry

        # Return JID
        return cast(str, config_entry.data[CONF_BEOLINK_JID])

    async def _async_update_sound_modes(
        self, active_sound_mode: ListeningModeProps | ListeningModeRef | None = None
    ) -> None:
        """Update the available sound modes."""
        sound_modes = await self._client.get_listening_mode_set()

        if active_sound_mode is None:
            active_sound_mode = await self._client.get_active_listening_mode()

        # Add the key to make the labels unique (As labels are not required to be unique on B&O devices)
        for sound_mode in sound_modes:
            label = f"{sound_mode.name} ({sound_mode.id})"

            self._sound_modes[label] = sound_mode.id

            if sound_mode.id == active_sound_mode.id:
                self._attr_sound_mode = label

        # Set available options
        self._attr_sound_mode_list = list(self._sound_modes)

        self.async_write_ha_state()

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Flag media player features that are supported."""
        features = BANG_OLUFSEN_FEATURES

        # Add seeking if supported by the current source
        if self._source_change.is_seekable is True:
            features |= MediaPlayerEntityFeature.SEEK

        return features

    @property
    def state(self) -> MediaPlayerState:
        """Return the current state of the media player."""
        return BANG_OLUFSEN_STATES[self._state]

    @property
    def volume_level(self) -> float | None:
        """Volume level of the media player (0..1)."""
        if self._volume.level and self._volume.level.level is not None:
            return float(self._volume.level.level / 100)
        return None

    @property
    def is_volume_muted(self) -> bool | None:
        """Boolean if volume is currently muted."""
        if self._volume.muted and self._volume.muted.muted:
            return self._volume.muted.muted
        return None

    @property
    def media_content_type(self) -> str:
        """Return the current media type."""
        # Hard to determine content type
        if self._source_change.id == BangOlufsenSource.URI_STREAMER.id:
            return MediaType.URL
        return MediaType.MUSIC

    @property
    def media_duration(self) -> int | None:
        """Return the total duration of the current track in seconds."""
        return self._playback_metadata.total_duration_seconds

    @property
    def media_position(self) -> int | None:
        """Return the current playback progress."""
        return self._playback_progress.progress

    @property
    def media_image_url(self) -> str | None:
        """Return URL of the currently playing music."""
        return self._media_image.url

    @property
    def media_image_remotely_accessible(self) -> bool:
        """Return whether or not the image of the current media is available outside the local network."""
        return not self._media_image.has_local_image

    @property
    def media_title(self) -> str | None:
        """Return the currently playing title."""
        return self._playback_metadata.title

    @property
    def media_album_name(self) -> str | None:
        """Return the currently playing album name."""
        return self._playback_metadata.album_name

    @property
    def media_album_artist(self) -> str | None:
        """Return the currently playing artist name."""
        return self._playback_metadata.artist_name

    @property
    def media_track(self) -> int | None:
        """Return the currently playing track."""
        return self._playback_metadata.track

    @property
    def media_channel(self) -> str | None:
        """Return the currently playing channel."""
        return self._playback_metadata.organization

    @property
    def source(self) -> str | None:
        """Return the current audio source."""
        return self._source_change.name

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return information that is not returned anywhere else."""
        attributes: dict[str, Any] = {}

        # Add media id attribute
        if self._media_id_attribute:
            attributes.update({"media_id": self._media_id_attribute})

        # Add input signal attribute
        if self._input_signal_attribute:
            attributes.update({"input_signal": self._input_signal_attribute})

        # Add Beolink attributes
        if self._beolink_attributes:
            attributes.update(self._beolink_attributes)

        # Add favourite attributes
        if self._favourite_attribute:
            attributes.update(self._favourite_attribute)

        return attributes

    async def async_turn_off(self) -> None:
        """Set the device to "networkStandby"."""
        await self._client.post_standby()

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level, range 0..1."""

        new_volume = int(volume * 100)

        # Ensure that volume is not set higher than allowed by the device.
        if (
            self._volume.maximum
            and self._volume.maximum.level
            and new_volume > self._volume.maximum.level
        ):
            _LOGGER.warning(
                "Can't set volume to %s because it is higher than %s, which is the current configured maximum volume. Setting to max volume",
                volume,
                self._volume.maximum.level,
            )
            new_volume = self._volume.maximum.level

        await self._client.set_current_volume_level(
            volume_level=VolumeLevel(level=new_volume)
        )

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute or unmute media player."""
        await self._client.set_volume_mute(volume_mute=VolumeMute(muted=mute))

    async def async_media_play_pause(self) -> None:
        """Toggle play/pause media player."""
        if self.state == MediaPlayerState.PLAYING:
            await self.async_media_pause()
        elif self.state in (MediaPlayerState.PAUSED, MediaPlayerState.IDLE):
            await self.async_media_play()

    async def async_media_pause(self) -> None:
        """Pause media player."""
        await self._client.post_playback_command(command="pause")

    async def async_media_play(self) -> None:
        """Play media player."""
        await self._client.post_playback_command(command="play")

    async def async_media_stop(self) -> None:
        """Pause media player."""
        await self._client.post_playback_command(command="stop")

    async def async_media_next_track(self) -> None:
        """Send the next track command."""
        await self._client.post_playback_command(command="skip")

    async def async_media_seek(self, position: float) -> None:
        """Seek to position in ms."""
        await self._client.seek_to_position(position_ms=int(position * 1000))
        # Try to prevent the playback progress from bouncing in the UI.
        self._attr_media_position_updated_at = utcnow()
        self._playback_progress = PlaybackProgress(progress=int(position))

        self.async_write_ha_state()

    async def async_media_previous_track(self) -> None:
        """Send the previous track command."""
        await self._client.post_playback_command(command="prev")

    async def async_clear_playlist(self) -> None:
        """Clear the current playback queue."""
        await self._client.post_clear_queue()

    async def async_set_shuffle(self, shuffle: bool) -> None:
        """Set playback queues to shuffle."""
        await self._client.set_settings_queue(
            play_queue_settings=PlayQueueSettings(shuffle=shuffle),
        )

    async def async_set_repeat(self, repeat: RepeatMode) -> None:
        """Set playback queues to repeat."""
        await self._client.set_settings_queue(
            play_queue_settings=PlayQueueSettings(
                repeat=BANG_OLUFSEN_REPEAT_FROM_HA[repeat]
            )
        )

    async def async_select_source(self, source: str) -> None:
        """Select an input source."""
        if source not in self._sources.values():
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_source",
                translation_placeholders={
                    "invalid_source": source,
                    "valid_sources": ", ".join(list(self._sources.values())),
                },
            )

        key = [x for x in self._sources if self._sources[x] == source][0]

        # Check for source type
        if source in self._audio_sources.values():
            # Audio
            await self._client.set_active_source(source_id=key)
        else:
            # Video
            await self._client.post_remote_trigger(id=key)

    async def async_select_sound_mode(self, sound_mode: str) -> None:
        """Select a sound mode."""
        # Ensure only known sound modes known by the integration can be activated.
        if sound_mode not in self._sound_modes:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_sound_mode",
                translation_placeholders={
                    "invalid_sound_mode": sound_mode,
                    "valid_sound_modes": ", ".join(list(self._sound_modes)),
                },
            )

        await self._client.activate_listening_mode(id=self._sound_modes[sound_mode])

    async def async_play_media(
        self,
        media_type: MediaType | str,
        media_id: str,
        announce: bool | None = None,
        **kwargs: Any,
    ) -> None:
        """Play from: netradio station id, URI, favourite or Deezer."""
        # Convert audio/mpeg, audio/aac etc. to MediaType.MUSIC
        if media_type.startswith("audio/"):
            media_type = MediaType.MUSIC

        if media_type not in VALID_MEDIA_TYPES:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_media_type",
                translation_placeholders={
                    "invalid_media_type": media_type,
                    "valid_media_types": ",".join(VALID_MEDIA_TYPES),
                },
            )

        if media_source.is_media_source_id(media_id):
            sourced_media = await media_source.async_resolve_media(
                self.hass, media_id, self.entity_id
            )

            media_id = async_process_play_media_url(self.hass, sourced_media.url)

            # Exit if the source uses unsupported file.
            if media_id.endswith(".m3u"):
                raise HomeAssistantError(
                    translation_domain=DOMAIN, translation_key="m3u_invalid_format"
                )

        if announce:
            extra = kwargs.get(ATTR_MEDIA_EXTRA, {})

            absolute_volume = extra.get("overlay_absolute_volume", None)
            offset_volume = extra.get("overlay_offset_volume", None)
            tts_language = extra.get("overlay_tts_language", "en-us")

            # Construct request
            overlay_play_request = OverlayPlayRequest()

            # Define volume level
            if absolute_volume:
                overlay_play_request.volume_absolute = absolute_volume

            elif offset_volume:
                # Ensure that the volume is not above 100
                if not self._volume.level or not self._volume.level.level:
                    _LOGGER.warning("Error setting volume")
                else:
                    overlay_play_request.volume_absolute = min(
                        self._volume.level.level + offset_volume, 100
                    )

            if media_type == BangOlufsenMediaType.OVERLAY_TTS:
                # Bang & Olufsen cloud TTS
                overlay_play_request.text_to_speech = (
                    OverlayPlayRequestTextToSpeechTextToSpeech(
                        lang=tts_language, text=media_id
                    )
                )
            else:
                overlay_play_request.uri = Uri(location=media_id)

            await self._client.post_overlay_play(overlay_play_request)

        elif media_type in (MediaType.URL, MediaType.MUSIC):
            await self._client.post_uri_source(uri=Uri(location=media_id))

        # The "provider" media_type may not be suitable for overlay all the time.
        # Use it for now.
        elif media_type == BangOlufsenMediaType.TTS:
            await self._client.post_overlay_play(
                overlay_play_request=OverlayPlayRequest(
                    uri=Uri(location=media_id),
                )
            )

        elif media_type == BangOlufsenMediaType.RADIO:
            await self._client.run_provided_scene(
                scene_properties=SceneProperties(
                    action_list=[
                        Action(
                            type="radio",
                            radio_station_id=media_id,
                        )
                    ]
                )
            )

        elif media_type == BangOlufsenMediaType.FAVOURITE:
            await self._client.activate_preset(id=int(media_id))

        elif media_type in (BangOlufsenMediaType.DEEZER, BangOlufsenMediaType.TIDAL):
            try:
                # Play Deezer flow.
                if media_id == "flow" and media_type == BangOlufsenMediaType.DEEZER:
                    deezer_id = None

                    if "id" in kwargs[ATTR_MEDIA_EXTRA]:
                        deezer_id = kwargs[ATTR_MEDIA_EXTRA]["id"]

                    await self._client.start_deezer_flow(
                        user_flow=UserFlow(user_id=deezer_id)
                    )

                # Play a playlist or album.
                elif any(match in media_id for match in ("playlist", "album")):
                    start_from = 0
                    if "start_from" in kwargs[ATTR_MEDIA_EXTRA]:
                        start_from = kwargs[ATTR_MEDIA_EXTRA]["start_from"]

                    await self._client.add_to_queue(
                        play_queue_item=PlayQueueItem(
                            provider=PlayQueueItemType(value=media_type),
                            start_now_from_position=start_from,
                            type="playlist",
                            uri=media_id,
                        )
                    )

                # Play a track.
                else:
                    await self._client.add_to_queue(
                        play_queue_item=PlayQueueItem(
                            provider=PlayQueueItemType(value=media_type),
                            start_now_from_position=0,
                            type="track",
                            uri=media_id,
                        )
                    )

            except ApiException as error:
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key="play_media_error",
                    translation_placeholders={
                        "media_type": media_type,
                        "error_message": json.loads(error.body)["message"],
                    },
                ) from error

    async def async_browse_media(
        self,
        media_content_type: MediaType | str | None = None,
        media_content_id: str | None = None,
    ) -> BrowseMedia:
        """Implement the WebSocket media browsing helper."""
        return await media_source.async_browse_media(
            self.hass,
            media_content_id,
            content_filter=lambda item: item.media_content_type.startswith("audio/"),
        )

    async def async_join_players(self, group_members: list[str]) -> None:
        """Create a Beolink session with defined group members."""

        # Use the touch to join if no entities have been defined
        # Touch to join will make the device connect to any other currently-playing
        # Beolink compatible B&O device.
        # Repeated presses / calls will cycle between compatible playing devices.
        if len(group_members) == 0:
            await self.async_beolink_join()
            return

        # Get JID for each group member
        jids = [self._get_beolink_jid(group_member) for group_member in group_members]
        await self.async_beolink_expand(jids)

    async def async_unjoin_player(self) -> None:
        """Unjoin Beolink session. End session if leader."""
        await self._client.post_beolink_leave()

    # Custom services:
    async def async_beolink_join(
        self, beolink_jid: str | None = None, source_id: str | None = None
    ) -> ServiceResponse:
        """Join a Beolink multi-room experience."""
        # Touch to join
        if beolink_jid is None:
            response = await self._client.join_latest_beolink_experience()
        # Join a peer
        elif beolink_jid and source_id is None:
            response = await self._client.join_beolink_peer(jid=beolink_jid)
        # Join a peer and select specific source
        elif beolink_jid and source_id:
            # Beolink Converter NL/ML sources need to be in upper case
            if source_id in BEOLINK_JOIN_SOURCES_TO_UPPER:
                source_id = source_id.upper()

            response = await self._client.join_beolink_peer(
                jid=beolink_jid, source=source_id
            )

        retrieved_response = await self._client.async_get_beolink_join_result(
            response.request_id
        )
        return (
            retrieved_response.dict()
            if retrieved_response is not None
            else response.dict()
        )

    async def async_beolink_expand(
        self, beolink_jids: list[str] | None = None, all_discovered: bool = False
    ) -> ServiceResponse:
        """Expand a Beolink multi-room experience with a device or devices."""

        # Ensure that the current source is expandable
        if not self._beolink_sources[cast(str, self._source_change.id)]:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_source",
                translation_placeholders={
                    "invalid_source": cast(str, self._source_change.id),
                    "valid_sources": ", ".join(list(self._beolink_sources)),
                },
            )

        # Ensure that the current device is playing
        if self.state != MediaPlayerState.PLAYING:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="beolink_not_playing",
            )

        result: JsonObjectType = {}

        # Expand to all discovered devices
        if all_discovered:
            peers = await self._client.get_beolink_peers()

            for peer in peers:
                response = await self._client.async_post_beolink_expand(peer.jid)

                # Add result
                result[peer.jid] = {
                    "result": response if response is True else type(response).__name__
                }

        # Try to expand to all defined devices
        elif beolink_jids:
            for beolink_jid in beolink_jids:
                response = await self._client.async_post_beolink_expand(beolink_jid)

                # Add result
                result[beolink_jid] = {
                    "result": response if response is True else type(response).__name__
                }

        return result

    async def async_beolink_unexpand(self, beolink_jids: list[str]) -> None:
        """Unexpand a Beolink multi-room experience with a device or devices."""
        # Unexpand all defined devices
        for beolink_jid in beolink_jids:
            await self._client.post_beolink_unexpand(jid=beolink_jid)

    async def async_beolink_leave(self) -> None:
        """Leave the current Beolink experience."""
        await self._client.post_beolink_leave()

    async def async_beolink_allstandby(self) -> None:
        """Set all connected Beolink devices to standby."""
        await self._client.post_beolink_allstandby()

    async def async_beolink_listener_command(
        self, command: str, parameter: str | None = None
    ) -> None:
        """Receive a command from the Beolink leader."""
        for command_list in ACCEPTED_COMMANDS_LISTS:
            if command in command_list:
                # Get the parameter type.
                parameter_type: type[float | bool | str] | None = command_list[-1]

                # Run the command.
                if parameter is not None:
                    await getattr(self, f"async_{command}")(parameter_type(parameter))  # type: ignore[misc]

                elif parameter_type is None:
                    await getattr(self, f"async_{command}")()

                return

    async def async_beolink_leader_command(
        self, command: str, parameter: float | bool | str | None = None
    ) -> None:
        """Send a command to the Beolink leader."""
        for command_list in ACCEPTED_COMMANDS_LISTS:
            if command in command_list:
                # Get the parameter type.
                parameter_type: type[float | bool | str] | None = command_list[-1]

                # Check for valid parameter type.
                if parameter_type is not None:
                    try:
                        # Test the cast before assigning
                        parameter = parameter_type(parameter)  # type: ignore[arg-type]
                    except (ValueError, TypeError, Exception) as error:
                        raise HomeAssistantError(
                            translation_domain=DOMAIN,
                            translation_key="invalid_beolink_parameter",
                            translation_placeholders={
                                "parameter": str(parameter),
                                "parameter_type": parameter_type.__name__,
                                "command": command,
                            },
                        ) from error

                elif parameter_type is None and parameter is not None:
                    raise HomeAssistantError(
                        translation_domain=DOMAIN,
                        translation_key="invalid_beolink_parameter",
                        translation_placeholders={
                            "parameter": parameter,  # type: ignore[dict-item]
                            "parameter_type": str(parameter_type),
                            "command": command,
                        },
                    )

                # Forward the command to the leader if a listener.
                if self._remote_leader is not None:
                    async_dispatcher_send(
                        self.hass,
                        f"{self._remote_leader.jid}_{BEOLINK_LEADER_COMMAND}",
                        command,
                        parameter,
                    )

                # Run the command if leader.
                elif parameter is not None:
                    await getattr(self, f"async_{command}")(parameter_type(parameter))  # type: ignore[misc]

                elif parameter_type is None:
                    await getattr(self, f"async_{command}")()

                return

    async def async_beolink_set_volume(self, volume_level: str) -> None:
        """Set volume level for all connected Beolink devices."""

        # Get the remote leader to send the volume command to listeners
        if self._remote_leader is not None:
            async_dispatcher_send(
                self.hass,
                f"{self._remote_leader.jid}_{BEOLINK_VOLUME}",
                volume_level,
            )

        else:
            await self.async_set_volume_level(volume=float(volume_level))

            for beolink_listener in self._beolink_listeners:
                async_dispatcher_send(
                    self.hass,
                    f"{beolink_listener.jid}_{BEOLINK_LISTENER_COMMAND}",
                    "set_volume_level",
                    volume_level,
                )

    async def async_set_relative_volume_level(self, volume: float) -> None:
        """Set a volume level relative to the current level."""
        current_volume_level = self.volume_level

        # Handle if the volume level is not set
        if current_volume_level is None:
            current_volume_level = 0

        # Ensure that volume level behaves as expected
        if current_volume_level + volume >= 1.0:
            new_volume = 1.0
        elif current_volume_level + volume <= 0:
            new_volume = 0.0
        else:
            new_volume = current_volume_level + volume

        await self.async_set_volume_level(volume=new_volume)

    async def async_beolink_set_relative_volume(self, volume_level: str) -> None:
        """Set a volume level to adjust current volume level for all connected Beolink devices."""

        # Get the remote leader to send the volume command to listeners
        if self._remote_leader is not None:
            async_dispatcher_send(
                self.hass,
                f"{self._remote_leader.jid}_{BEOLINK_RELATIVE_VOLUME}",
                volume_level,
            )

        else:
            await self.async_set_relative_volume_level(volume=float(volume_level))

            for beolink_listener in self._beolink_listeners:
                async_dispatcher_send(
                    self.hass,
                    f"{beolink_listener.jid}_{BEOLINK_LISTENER_COMMAND}",
                    "set_relative_volume_level",
                    volume_level,
                )

    async def async_reboot(self) -> None:
        """Reboot the device."""
        await self._client.post_reboot()
