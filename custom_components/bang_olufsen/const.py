"""Constants for the Bang & Olufsen integration."""

from __future__ import annotations

from enum import Enum, StrEnum
from typing import Final

from mozart_api.models import Source, SourceArray, SourceTypeEnum

from homeassistant.components.media_player import MediaPlayerState, MediaType


class BangOlufsenSource:
    """Class used for associating device source ids with friendly names. May not include all sources."""

    URI_STREAMER: Final[Source] = Source(name="Audio Streamer", id="uriStreamer")
    BLUETOOTH: Final[Source] = Source(name="Bluetooth", id="bluetooth")
    CHROMECAST: Final[Source] = Source(name="Chromecast built-in", id="chromeCast")
    LINE_IN: Final[Source] = Source(name="Line-In", id="lineIn")
    SPDIF: Final[Source] = Source(name="Optical", id="spdif")
    NET_RADIO: Final[Source] = Source(name="B&O Radio", id="netRadio")
    DEEZER: Final[Source] = Source(name="Deezer", id="deezer")
    TIDAL: Final[Source] = Source(name="Tidal", id="tidal")
    USB_IN: Final[Source] = Source(name="USB", id="usbIn")
    UNKNOWN: Final[Source] = Source(name="Unknown Source", id="unknown")


class BangOlufsenRepeat(StrEnum):
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
}


# Media types for play_media
class BangOlufsenMediaType(StrEnum):
    """Bang & Olufsen specific media types."""

    DEEZER = "deezer"
    FAVOURITE = "favourite"
    OVERLAY_TTS = "overlay_tts"
    RADIO = "radio"
    TIDAL = "tidal"
    TTS = "provider"


# Proximity detection for binary_sensor
class BangOlufsenProximity(Enum):
    """Proximity detection mapping.."""

    proximityPresenceDetected = True  # noqa: N815
    proximityPresenceNotDetected = False  # noqa: N815


class BangOlufsenModel(StrEnum):
    """Enum for compatible model names."""

    BEOCONNECT_CORE = "Beoconnect Core"
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
class WebsocketNotification(StrEnum):
    """Enum for WebSocket notification types."""

    ACTIVE_LISTENING_MODE = "active_listening_mode"
    ACTIVE_SPEAKER_GROUP = "active_speaker_group"
    ALARM_TRIGGERED = "alarm_triggered"
    BATTERY = "battery"
    BEO_REMOTE_BUTTON = "beo_remote_button"
    BEOLINK_EXPERIENCES_RESULT = "beolink_experiences_result"
    BEOLINK_JOIN_RESULT = "beolink_join_result"
    BUTTON = "button"
    CURTAINS = "curtains"
    PLAYBACK_ERROR = "playback_error"
    PLAYBACK_METADATA = "playback_metadata"
    PLAYBACK_PROGRESS = "playback_progress"
    PLAYBACK_SOURCE = "playback_source"
    PLAYBACK_STATE = "playback_state"
    POWER_STATE = "power_state"
    ROLE = "role"
    SOFTWARE_UPDATE_STATE = "software_update_state"
    SOUND_SETTINGS = "sound_settings"
    SOURCE_CHANGE = "source_change"
    VOLUME = "volume"

    # Sub-notifications
    BEOLINK = "beolink"
    BEOLINK_AVAILABLE_LISTENERS = "beolinkAvailableListeners"
    BEOLINK_LISTENERS = "beolinkListeners"
    BEOLINK_PEERS = "beolinkPeers"
    BLUETOOTH_DEVICES = "bluetooth"
    CONFIGURATION = "configuration"
    NOTIFICATION = "notification"
    PROXIMITY = "proximity"
    PROXIMITY_PRESENCE_DETECTED = "proximityPresenceDetected"
    PROXIMITY_PRESENCE_NOT_DETECTED = "proximityPresenceNotDetected"
    REMOTE_CONTROL_DEVICES = "remoteControlDevices"
    REMOTE_MENU_CHANGED = "remoteMenuChanged"

    ALL = "all"


class BangOlufsenModelSupport(Enum):
    """Enum for storing compatibility of devices."""

    PROXIMITY_SENSOR = (
        BangOlufsenModel.BEOLAB_8,
        BangOlufsenModel.BEOLAB_28,
        BangOlufsenModel.BEOSOUND_2,
        BangOlufsenModel.BEOSOUND_BALANCE,
        BangOlufsenModel.BEOSOUND_LEVEL,
        BangOlufsenModel.BEOSOUND_THEATRE,
    )

    HOME_CONTROL = (BangOlufsenModel.BEOSOUND_THEATRE,)


# Range for bass and treble entities
BASS_TREBLE_RANGE = range(-6, 6, 1)

DOMAIN: Final[str] = "bang_olufsen"

# Default values for configuration.
DEFAULT_MODEL: Final[str] = BangOlufsenModel.BEOSOUND_BALANCE

# Configuration.
CONF_BEOLINK_JID: Final = "jid"
CONF_SERIAL_NUMBER: Final = "serial_number"

# Models to choose from in manual configuration.
COMPATIBLE_MODELS: list[str] = [x.value for x in BangOlufsenModel]

# Attribute names for zeroconf discovery.
ATTR_TYPE_NUMBER: Final[str] = "tn"
ATTR_SERIAL_NUMBER: Final[str] = "sn"
ATTR_ITEM_NUMBER: Final[str] = "in"
ATTR_FRIENDLY_NAME: Final[str] = "fn"

# Power states.
BANG_OLUFSEN_ON: Final[str] = "on"

VALID_MEDIA_TYPES: Final[tuple] = (
    BangOlufsenMediaType.DEEZER,
    BangOlufsenMediaType.FAVOURITE,
    BangOlufsenMediaType.OVERLAY_TTS,
    BangOlufsenMediaType.RADIO,
    BangOlufsenMediaType.TIDAL,
    BangOlufsenMediaType.TTS,
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

# Dict used to translate native Bang & Olufsen event names to string.json compatible ones
EVENT_TRANSLATION_MAP: dict[str, str] = {
    "KeyPress": "key_press",
    "KeyRelease": "key_release",
    "shortPress (Release)": "short_press_release",
    "longPress (Timeout)": "long_press_timeout",
    "longPress (Release)": "long_press_release",
    "veryLongPress (Timeout)": "very_long_press_timeout",
    "veryLongPress (Release)": "very_long_press_release",
    "proximityPresenceDetected": "proximity_presence_detected",
    "proximityPresenceNotDetected": "proximity_presence_not_detected",
}

DEVICE_BUTTONS: Final[list[str]] = [
    "Bluetooth",
    "Microphone",
    "Next",
    "PlayPause",
    "Preset1",
    "Preset2",
    "Preset3",
    "Preset4",
    "Previous",
    "Volume",
]


DEVICE_BUTTON_EVENTS: Final[list[str]] = [
    "short_press_release",
    "long_press_timeout",
    "long_press_release",
    "very_long_press_timeout",
    "very_long_press_release",
]


BEO_REMOTE_SUBMENU_CONTROL: Final[str] = "Control"
BEO_REMOTE_SUBMENU_LIGHT: Final[str] = "Light"

# Common for both submenus
BEO_REMOTE_KEYS: Final[tuple[str, ...]] = (
    "Blue",
    "Digit0",
    "Digit1",
    "Digit2",
    "Digit3",
    "Digit4",
    "Digit5",
    "Digit6",
    "Digit7",
    "Digit8",
    "Digit9",
    "Down",
    "Green",
    "Left",
    "Play",
    "Red",
    "Rewind",
    "Right",
    "Select",
    "Stop",
    "Up",
    "Wind",
    "Yellow",
)

# "keys" that are unique to the Control and Light submenus
BEO_REMOTE_CONTROL_KEYS: Final[tuple[str, ...]] = (
    "Func1",
    "Func11",
    "Func16",
    "Func6",
)

BEO_REMOTE_LIGHT_KEYS: Final[tuple[str, ...]] = (
    "Func1",
    "Func11",
    "Func12",
    "Func13",
    "Func14",
    "Func15",
    "Func16",
    "Func17",
)

BEO_REMOTE_KEY_EVENTS: Final[list[str]] = ["key_press", "key_release"]

PROXIMITY_EVENTS: Final[list[str]] = [
    "proximity_presence_detected",
    "proximity_presence_not_detected",
]


BEOLINK_LEADER_COMMAND: Final[str] = "BEOLINK_LEADER_COMMAND"
BEOLINK_LISTENER_COMMAND: Final[str] = "BEOLINK_LISTENER_COMMAND"
BEOLINK_VOLUME: Final[str] = "BEOLINK_VOLUME"
BEOLINK_RELATIVE_VOLUME: Final[str] = "BEOLINK_RELATIVE_VOLUME"


# Valid commands and their expected parameter type for beolink_command service
FLOAT_PARAMETERS: Final[tuple[str, str, str, type[float]]] = (
    "set_volume_level",
    "media_seek",
    "set_relative_volume_level",
    float,
)
BOOL_PARAMETERS: Final[tuple[str, type[bool]]] = ("mute_volume", bool)
STR_PARAMETERS: Final[tuple[str, type[str]]] = ("select_source", str)
NONE_PARAMETERS: Final[tuple[str, str, str, str, str, str, str, str, None]] = (
    "volume_up",
    "volume_down",
    "media_play_pause",
    "media_pause",
    "media_play",
    "media_stop",
    "media_next_track",
    "media_previous_track",
    None,
)

# Tuple of accepted commands for input validation
ACCEPTED_COMMANDS: Final[tuple[tuple[str]]] = (
    FLOAT_PARAMETERS[:-1]  # type: ignore[assignment]
    + BOOL_PARAMETERS[:-1]
    + STR_PARAMETERS[:-1]
    + NONE_PARAMETERS[:-1]
)

# Tuple of all commands and their types for executing commands.
ACCEPTED_COMMANDS_LISTS: tuple[
    tuple[str, str, str, type[float]],
    tuple[str, type[bool]],
    tuple[str, type[str]],
    tuple[str, str, str, str, str, str, str, str, None],
] = (
    FLOAT_PARAMETERS,
    BOOL_PARAMETERS,
    STR_PARAMETERS,
    NONE_PARAMETERS,
)
