"""Constants for the Bang & Olufsen integration."""

from __future__ import annotations

from enum import StrEnum
from typing import Final, TypedDict

from mozart_api.models import Source, SourceTypeEnum

from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_CURRENT_TILT_POSITION,
    ATTR_POSITION,
    ATTR_TILT_POSITION,
)
from homeassistant.components.media_player import (
    MediaPlayerState,
    MediaType,
    RepeatMode,
)
from homeassistant.const import (
    SERVICE_SET_COVER_POSITION,
    SERVICE_SET_COVER_TILT_POSITION,
)

from .beoremote_halo.models import Icons, SystemEventState


class BeoSource:
    """Class used for associating device source ids with friendly names. May not include all sources."""

    DEEZER: Final[Source] = Source(name="Deezer", id="deezer")
    LINE_IN: Final[Source] = Source(name="Line-In", id="lineIn")
    NET_RADIO: Final[Source] = Source(name="B&O Radio", id="netRadio")
    SPDIF: Final[Source] = Source(name="Optical", id="spdif")
    TIDAL: Final[Source] = Source(name="Tidal", id="tidal")
    TV: Final[Source] = Source(name="TV", id="tv")
    UNKNOWN: Final[Source] = Source(name="Unknown Source", id="unknown")
    URI_STREAMER: Final[Source] = Source(name="Audio Streamer", id="uriStreamer")
    USB_IN: Final[Source] = Source(name="USB", id="usbIn")


BEO_STATES: dict[str, MediaPlayerState] = {
    # Dict used for translating device states to Home Assistant states.
    "started": MediaPlayerState.PLAYING,
    "buffering": MediaPlayerState.PLAYING,
    "idle": MediaPlayerState.IDLE,
    "paused": MediaPlayerState.PAUSED,
    "stopped": MediaPlayerState.IDLE,
    "ended": MediaPlayerState.PAUSED,
    "error": MediaPlayerState.IDLE,
    # A device's initial state is "unknown" and should be treated as "idle"
    "unknown": MediaPlayerState.IDLE,
}

# Dict used for translating Home Assistant settings to device repeat settings.
BEO_REPEAT_FROM_HA: dict[RepeatMode, str] = {
    RepeatMode.ALL: "all",
    RepeatMode.ONE: "track",
    RepeatMode.OFF: "none",
}
# Dict used for translating device repeat settings to Home Assistant settings.
BEO_REPEAT_TO_HA: dict[str, RepeatMode] = {
    value: key for key, value in BEO_REPEAT_FROM_HA.items()
}


# Media types for play_media
class BeoMediaType(StrEnum):
    """Bang & Olufsen specific media types."""

    DEEZER = "deezer"
    FAVOURITE = "favourite"
    OVERLAY_TTS = "overlay_tts"
    RADIO = "radio"
    TIDAL = "tidal"
    TTS = "provider"
    TV = "tv"


class BeoModel(StrEnum):
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
    BEOSOUND_PREMIERE = "Beosound Premiere"
    BEOSOUND_THEATRE = "Beosound Theatre"
    BEOREMOTE_HALO = "Beoremote Halo"
    BEOREMOTE_ONE = "Beoremote One"


class BeoAttribute(StrEnum):
    """Enum for extra_state_attribute keys."""

    BEOLINK = "beolink"
    BEOLINK_LEADER = "leader"
    BEOLINK_LISTENERS = "listeners"
    BEOLINK_PEERS = "peers"
    BEOLINK_SELF = "self"
    FAVORITES = "favorites"
    FAVORITES_CONTENT_ID = "content_id"
    FAVORITES_SOURCE = "source"
    FAVORITES_TITLE = "title"
    INPUT_SIGNAL = "input_signal"


# Physical "buttons" on devices
class BeoButtons(StrEnum):
    """Enum for device buttons."""

    BLUETOOTH = "Bluetooth"
    MICROPHONE = "Microphone"
    NEXT = "Next"
    PLAY_PAUSE = "PlayPause"
    PRESET_1 = "Preset1"
    PRESET_2 = "Preset2"
    PRESET_3 = "Preset3"
    PRESET_4 = "Preset4"
    PREVIOUS = "Previous"
    VOLUME = "Volume"


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

    # Halo notifications
    HALO_WHEEL = "halo_wheel"
    HALO_SYSTEM = "halo_system"
    HALO_STATUS = "halo_status"
    HALO_POWER = "halo_power"
    HALO_BUTTON = "halo_button"


DOMAIN: Final[str] = "bang_olufsen"

# Default values for configuration.
DEFAULT_MODEL: Final[str] = BeoModel.BEOSOUND_BALANCE

# Configuration.
CONF_BEOLINK_JID: Final = "jid"
CONF_SERIAL_NUMBER: Final = "serial_number"

# Halo configuration
CONF_PAGE_TITLE: Final = "page_title"
CONF_BUTTON_TITLE: Final = "button_title"
CONF_PAGES: Final = "pages"
CONF_VALUE: Final = "value"
CONF_HALO: Final = "halo"
CONF_ENTITY_MAP: Final = "entity_map"
CONF_DEFAULT_BUTTON: Final = "default_button"
CONF_BUTTON_ACTION: Final = "button_action"
CONF_WHEEL_ACTION: Final = "wheel_action"
# Menu options / step IDs
HALO_OPTION_PAGE = "page"
HALO_OPTION_MODIFY_PAGE = "modify_page"
HALO_OPTION_DELETE_PAGES = "delete_pages"
HALO_OPTION_MODIFY_DEFAULT = "modify_default"
HALO_OPTION_SELECT_DEFAULT = "select_default"
HALO_OPTION_REMOVE_DEFAULT = "remove_default"

# The names of compatible button icons for the Beoremote Halo
HALO_BUTTON_ICONS: list[str] = [icon.name for icon in Icons]

# Timeout for sending wheel events in seconds
HALO_WHEEL_TIMEOUT: Final = 0.250


class EntityMapActionValues(TypedDict):
    """Actions that a button should use."""

    button_action: str | None
    wheel_action: str | None


class EntityMapValues(EntityMapActionValues):
    """TypedDict for Halo button information and settings."""

    entity_id: str


# Associate cover actions with their attributes
COVER_ATTRIBUTE_MAP: Final[dict[str, tuple[str, str]]] = {
    SERVICE_SET_COVER_POSITION: (ATTR_CURRENT_POSITION, ATTR_POSITION),
    SERVICE_SET_COVER_TILT_POSITION: (ATTR_CURRENT_TILT_POSITION, ATTR_TILT_POSITION),
}

# Mozart models
MOZART_MODELS: Final[list[BeoModel]] = [
    model
    for model in BeoModel
    if model.value not in (BeoModel.BEOREMOTE_HALO, BeoModel.BEOREMOTE_ONE)
]
# Models that can be setup manually
SELECTABLE_MODELS: Final[list[BeoModel]] = [
    model for model in BeoModel if model.value not in (BeoModel.BEOREMOTE_ONE)
]


MANUFACTURER: Final[str] = "Bang & Olufsen"

ZEROCONF_MOZART: Final[str] = "_bangolufsen._tcp.local."
ZEROCONF_HALO: Final[str] = "_zenith._tcp.local."

# Attribute names for zeroconf discovery.
ATTR_TYPE_NUMBER: Final[str] = "tn"
ATTR_MOZART_SERIAL_NUMBER: Final[str] = "sn"
ATTR_HALO_SERIAL_NUMBER: Final[str] = "serial"
ATTR_ITEM_NUMBER: Final[str] = "in"
ATTR_FRIENDLY_NAME: Final[str] = "fn"

# Power states.
BEO_ON: Final[str] = "on"

VALID_MEDIA_TYPES: Final[tuple[str, ...]] = (
    BeoMediaType.DEEZER,
    BeoMediaType.FAVOURITE,
    BeoMediaType.OVERLAY_TTS,
    BeoMediaType.RADIO,
    BeoMediaType.TIDAL,
    BeoMediaType.TTS,
    MediaType.MUSIC,
    MediaType.URL,
    MediaType.CHANNEL,
)

# Fallback sources to use in case of API failure.
FALLBACK_SOURCES: Final[list[Source]] = [
    Source(
        id="uriStreamer",
        is_enabled=True,
        is_playable=True,
        name="Audio Streamer",
        type=SourceTypeEnum(value="uriStreamer"),
        is_seekable=False,
    ),
    Source(
        id="bluetooth",
        is_enabled=True,
        is_playable=True,
        name="Bluetooth",
        type=SourceTypeEnum(value="bluetooth"),
        is_seekable=False,
    ),
    Source(
        id="spotify",
        is_enabled=True,
        is_playable=True,
        name="Spotify Connect",
        type=SourceTypeEnum(value="spotify"),
        is_seekable=True,
    ),
    Source(
        id="lineIn",
        is_enabled=True,
        is_playable=True,
        name="Line-In",
        type=SourceTypeEnum(value="lineIn"),
        is_seekable=False,
    ),
    Source(
        id="spdif",
        is_enabled=True,
        is_playable=True,
        name="Optical",
        type=SourceTypeEnum(value="spdif"),
        is_seekable=False,
    ),
    Source(
        id="netRadio",
        is_enabled=True,
        is_playable=True,
        name="B&O Radio",
        type=SourceTypeEnum(value="netRadio"),
        is_seekable=False,
    ),
    Source(
        id="deezer",
        is_enabled=True,
        is_playable=True,
        name="Deezer",
        type=SourceTypeEnum(value="deezer"),
        is_seekable=True,
    ),
    Source(
        id="tidalConnect",
        is_enabled=True,
        is_playable=True,
        name="Tidal Connect",
        type=SourceTypeEnum(value="tidalConnect"),
        is_seekable=True,
    ),
]


# Map for storing compatibility of devices.

MODEL_SUPPORT_PROXIMITY: Final[str] = "proximity_sensor"
MODEL_SUPPORT_HOME_CONTROL: Final[str] = "home_control"

MODEL_SUPPORT_MAP = {
    MODEL_SUPPORT_PROXIMITY: (
        BeoModel.BEOLAB_8,
        BeoModel.BEOLAB_28,
        BeoModel.BEOSOUND_2,
        BeoModel.BEOSOUND_BALANCE,
        BeoModel.BEOSOUND_LEVEL,
        BeoModel.BEOSOUND_THEATRE,
    ),
    MODEL_SUPPORT_HOME_CONTROL: (BeoModel.BEOSOUND_THEATRE,),
}


# Device events
MOZART_WEBSOCKET_EVENT: Final[str] = f"{DOMAIN}_websocket_event"
HALO_WEBSOCKET_EVENT: Final[str] = f"{DOMAIN}_halo_websocket_event"

# Dict used to translate native Bang & Olufsen event names to string.json compatible ones
EVENT_TRANSLATION_MAP: dict[str, str] = {
    # Beoremote One
    "KeyPress": "key_press",
    "KeyRelease": "key_release",
    # Physical "buttons"
    "shortPress (Release)": "short_press_release",
    "longPress (Timeout)": "long_press_timeout",
    "longPress (Release)": "long_press_release",
    "veryLongPress (Timeout)": "very_long_press_timeout",
    "veryLongPress (Release)": "very_long_press_release",
    # Proximity sensor
    "proximityPresenceDetected": "proximity_presence_detected",
    "proximityPresenceNotDetected": "proximity_presence_not_detected",
}

CONNECTION_STATUS: Final[str] = "CONNECTION_STATUS"

DEVICE_BUTTONS: Final[list[str]] = [x.value for x in BeoButtons]


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
    "Func1",
    "Func2",
    "Func3",
    "Func4",
    "Func5",
    "Func6",
    "Func7",
    "Func8",
    "Func9",
    "Func10",
    "Func11",
    "Func12",
    "Func13",
    "Func14",
    "Func15",
    "Func16",
    "Func17",
)

# "keys" that are unique to the Control submenu
BEO_REMOTE_CONTROL_KEYS: Final[tuple[str, ...]] = (
    "Func18",
    "Func19",
    "Func20",
    "Func21",
    "Func22",
    "Func23",
    "Func24",
    "Func25",
    "Func26",
    "Func27",
)


BEO_REMOTE_KEY_EVENTS: Final[list[str]] = ["key_press", "key_release"]

PROXIMITY_EVENTS: Final[list[str]] = [
    "proximity_presence_detected",
    "proximity_presence_not_detected",
]
HALO_SYSTEM_EVENTS: Final[list[str]] = list(SystemEventState)

# Beolink Converter NL/ML sources need to be transformed to upper case
BEOLINK_JOIN_SOURCES_TO_UPPER = (
    "aux_a",
    "cd",
    "ph",
    "radio",
    "tp1",
    "tp2",
)
BEOLINK_JOIN_SOURCES = (
    *BEOLINK_JOIN_SOURCES_TO_UPPER,
    "beoradio",
    "deezer",
    "spotify",
    "tidal",
)


BEOLINK_LEADER_COMMAND: Final[str] = "BEOLINK_LEADER_COMMAND"
BEOLINK_LISTENER_COMMAND: Final[str] = "BEOLINK_LISTENER_COMMAND"
BEOLINK_VOLUME: Final[str] = "BEOLINK_VOLUME"
BEOLINK_RELATIVE_VOLUME: Final[str] = "BEOLINK_RELATIVE_VOLUME"


# Valid commands and their expected parameter type for beolink_command action
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
