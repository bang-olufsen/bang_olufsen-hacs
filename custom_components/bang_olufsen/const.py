"""Constants for the Bang & Olufsen integration."""
from __future__ import annotations

from enum import Enum, StrEnum
from typing import Final

from mozart_api.models import Source, SourceArray, SourceTypeEnum

from homeassistant.components.media_player import MediaPlayerState, MediaType


class SOURCE_ENUM(StrEnum):
    """Enum used for associating device source ids with friendly names. May not include all sources."""

    uriStreamer = "Audio Streamer"  # noqa: N815
    bluetooth = "Bluetooth"
    airPlay = "AirPlay"  # noqa: N815
    chromeCast = "Chromecast built-in"  # noqa: N815
    spotify = "Spotify Connect"
    generator = "Tone Generator"
    lineIn = "Line-In"  # noqa: N815
    spdif = "Optical"
    netRadio = "B&O Radio"  # noqa: N815
    local = "Local"
    dlna = "DLNA"
    qplay = "QPlay"
    wpl = "Wireless Powerlink"
    pl = "Powerlink"
    tv = "TV"
    deezer = "Deezer"
    beolink = "Networklink"
    tidalConnect = "Tidal Connect"  # noqa: N815


class REPEAT_ENUM(StrEnum):
    """Enum used for translating device repeat settings to Home Assistant settings."""

    all = "all"
    one = "track"
    off = "none"


BANG_OLUFSEN_STATES: dict[str, MediaPlayerState] = {
    # Dict used for translating device states to Home Assistant states.
    "started": MediaPlayerState.PLAYING,
    "buffering": MediaPlayerState.PLAYING,
    "idle": MediaPlayerState.IDLE,
    "paused": MediaPlayerState.PAUSED,
    "stopped": MediaPlayerState.PAUSED,
    "ended": MediaPlayerState.PAUSED,
    "error": MediaPlayerState.IDLE,
    # A devices initial state is "unknown" and should be treated as "idle"
    "unknown": MediaPlayerState.IDLE,
    # Power states
}


# Media types for play_media
class BANG_OLUFSEN_MEDIA_TYPE(StrEnum):
    """Bang & Olufsen specific media types."""

    FAVOURITE = "favourite"
    DEEZER = "deezer"
    RADIO = "radio"
    TTS = "provider"


# Proximity detection for binary_sensor
class PROXIMITY_ENUM(Enum):
    """Proximity detection mapping.."""

    proximityPresenceDetected = True  # noqa: N815
    proximityPresenceNotDetected = False  # noqa: N815


class MODEL_ENUM(StrEnum):
    """Enum for compatible model names."""

    BEOLAB_8 = "BeoLab 8"
    BEOLAB_28 = "BeoLab 28"
    BEOSOUND_2 = "Beosound 2 3rd Gen"
    BEOSOUND_A5 = "Beosound A5"
    BEOSOUND_A9 = "Beosound A9 5th Gen"
    BEOSOUND_BALANCE = "Beosound Balance"
    BEOSOUND_EMERGE = "Beosound Emerge"
    BEOSOUND_LEVEL = "Beosound Level"
    BEOSOUND_THEATRE = "Beosound Theatre"


# Dispatcher events
class WEBSOCKET_NOTIFICATION(StrEnum):
    """Enum for WebSocket notification types."""

    ACTIVE_LISTENING_MODE: Final[str] = "active_listening_mode"
    ACTIVE_SPEAKER_GROUP: Final[str] = "active_speaker_group"
    ALARM_TRIGGERED: Final[str] = "alarm_triggered"
    BATTERY: Final[str] = "battery"
    BEOLINK_EXPERIENCES_RESULT: Final[str] = "beolink_experiences_result"
    BEOLINK_JOIN_RESULT: Final[str] = "beolink_join_result"
    BEO_REMOTE_BUTTON: Final[str] = "beo_remote_button"
    BUTTON: Final[str] = "button"
    CURTAINS: Final[str] = "curtains"
    PLAYBACK_ERROR: Final[str] = "playback_error"
    PLAYBACK_METADATA: Final[str] = "playback_metadata"
    PLAYBACK_PROGRESS: Final[str] = "playback_progress"
    PLAYBACK_SOURCE: Final[str] = "playback_source"
    PLAYBACK_STATE: Final[str] = "playback_state"
    POWER_STATE: Final[str] = "power_state"
    ROLE: Final[str] = "role"
    SOFTWARE_UPDATE_STATE: Final[str] = "software_update_state"
    SOUND_SETTINGS: Final[str] = "sound_settings"
    SOURCE_CHANGE: Final[str] = "source_change"
    VOLUME: Final[str] = "volume"

    # Sub-notifications
    NOTIFICATION: Final[str] = "notification"
    PROXIMITY: Final[str] = "proximity"
    BEOLINK: Final[str] = "beolink"
    REMOTE_MENU_CHANGED: Final[str] = "remoteMenuChanged"
    CONFIGURATION: Final[str] = "configuration"
    BLUETOOTH_DEVICES: Final[str] = "bluetooth"
    REMOTE_CONTROL_DEVICES: Final[str] = "remoteControlDevices"

    ALL: Final[str] = "all"


class SUPPORT_ENUM(Enum):
    """Enum for storing compatibility of devices."""

    PROXIMITY_SENSOR = (
        MODEL_ENUM.BEOLAB_8,
        MODEL_ENUM.BEOLAB_28,
        MODEL_ENUM.BEOSOUND_2,
        MODEL_ENUM.BEOSOUND_BALANCE,
        MODEL_ENUM.BEOSOUND_LEVEL,
        MODEL_ENUM.BEOSOUND_THEATRE,
    )

    HOME_CONTROL = (MODEL_ENUM.BEOSOUND_THEATRE,)


# Range for bass and treble entities
BASS_TREBLE_RANGE = range(-6, 6, 1)

DOMAIN: Final[str] = "bang_olufsen"

# Default values for configuration.
DEFAULT_MODEL: Final[str] = MODEL_ENUM.BEOSOUND_BALANCE

# Configuration.
CONF_BEOLINK_JID: Final = "jid"
CONF_SERIAL_NUMBER: Final = "serial_number"

# Models to choose from in manual configuration.
COMPATIBLE_MODELS: list[str] = [x.value for x in MODEL_ENUM]

# Attribute names for zeroconf discovery.
ATTR_TYPE_NUMBER: Final[str] = "tn"
ATTR_SERIAL_NUMBER: Final[str] = "sn"
ATTR_ITEM_NUMBER: Final[str] = "in"
ATTR_FRIENDLY_NAME: Final[str] = "fn"

# Power states.
BANG_OLUFSEN_ON: Final[str] = "on"

VALID_MEDIA_TYPES: Final[tuple] = (
    BANG_OLUFSEN_MEDIA_TYPE.FAVOURITE,
    BANG_OLUFSEN_MEDIA_TYPE.DEEZER,
    BANG_OLUFSEN_MEDIA_TYPE.RADIO,
    BANG_OLUFSEN_MEDIA_TYPE.TTS,
    MediaType.MUSIC,
    MediaType.URL,
    MediaType.CHANNEL,
)

# Playback states for playing and not playing
PLAYING: Final[tuple] = ("started", "buffering", BANG_OLUFSEN_ON)
NOT_PLAYING: Final[tuple] = ("idle", "paused", "stopped", "ended", "unknown", "error")

# Sources on the device that should not be selectable by the user
HIDDEN_SOURCE_IDS: Final[tuple] = (
    "airPlay",
    "bluetooth",
    "chromeCast",
    "generator",
    "local",
    "dlna",
    "qplay",
    "wpl",
    "pl",
    "beolink",
    "classicsAdapter",
    "usbIn",
)

# Fallback sources to use in case of API failure.
FALLBACK_SOURCES: Final[SourceArray] = SourceArray(
    items=[
        Source(
            id="uriStreamer",
            is_enabled=True,
            is_playable=False,
            name="Audio Streamer",
            type=SourceTypeEnum(value="uriStreamer"),
        ),
        Source(
            id="bluetooth",
            is_enabled=True,
            is_playable=False,
            name="Bluetooth",
            type=SourceTypeEnum(value="bluetooth"),
        ),
        Source(
            id="spotify",
            is_enabled=True,
            is_playable=False,
            name="Spotify Connect",
            type=SourceTypeEnum(value="spotify"),
        ),
        Source(
            id="lineIn",
            is_enabled=True,
            is_playable=True,
            name="Line-In",
            type=SourceTypeEnum(value="lineIn"),
        ),
        Source(
            id="spdif",
            is_enabled=True,
            is_playable=True,
            name="Optical",
            type=SourceTypeEnum(value="spdif"),
        ),
        Source(
            id="netRadio",
            is_enabled=True,
            is_playable=True,
            name="B&O Radio",
            type=SourceTypeEnum(value="netRadio"),
        ),
        Source(
            id="deezer",
            is_enabled=True,
            is_playable=True,
            name="Deezer",
            type=SourceTypeEnum(value="deezer"),
        ),
        Source(
            id="tidalConnect",
            is_enabled=True,
            is_playable=True,
            name="Tidal Connect",
            type=SourceTypeEnum(value="tidalConnect"),
        ),
    ]
)


# Device trigger events
BANG_OLUFSEN_EVENT: Final[str] = f"{DOMAIN}_event"
BANG_OLUFSEN_WEBSOCKET_EVENT: Final[str] = f"{DOMAIN}_websocket_event"


CONNECTION_STATUS: Final[str] = "CONNECTION_STATUS"
BEOLINK_LEADER_COMMAND: Final[str] = "BEOLINK_LEADER_COMMAND"
BEOLINK_LISTENER_COMMAND: Final[str] = "BEOLINK_LISTENER_COMMAND"
BEOLINK_VOLUME: Final[str] = "BEOLINK_VOLUME"
BEOLINK_RELATIVE_VOLUME: Final[str] = "BEOLINK_RELATIVE_VOLUME"


# Valid commands and their expected parameter type for beolink_command service
FLOAT_PARAMETERS: Final[tuple] = (
    "set_volume_level",
    "media_seek",
    "set_relative_volume_level",
    float,
)
BOOL_PARAMETERS: Final[tuple] = ("mute_volume", bool)
STR_PARAMETERS: Final[tuple] = ("select_source", str)
NONE_PARAMETERS: Final[tuple] = (
    "volume_up",
    "volume_down",
    "media_play_pause",
    "media_pause",
    "media_play",
    "media_stop",
    "media_next_track",
    "media_previous_track",
    "toggle",
    None,
)

# Tuple of accepted commands for input validation
ACCEPTED_COMMANDS: Final[tuple] = (
    FLOAT_PARAMETERS[:-1]
    + BOOL_PARAMETERS[:-1]
    + STR_PARAMETERS[:-1]
    + NONE_PARAMETERS[:-1]
)

# Tuple of all commands and their types for executing commands.
ACCEPTED_COMMANDS_LISTS: Final[tuple] = (
    FLOAT_PARAMETERS,
    BOOL_PARAMETERS,
    STR_PARAMETERS,
    NONE_PARAMETERS,
)