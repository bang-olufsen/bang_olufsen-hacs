"""Constants used for testing the bang_olufsen integration."""

from ipaddress import IPv4Address, IPv6Address
from unittest.mock import Mock

from mozart_api.exceptions import ApiException
from mozart_api.models import (
    Action,
    ListeningModeRef,
    OverlayPlayRequest,
    OverlayPlayRequestTextToSpeechTextToSpeech,
    PlaybackContentMetadata,
    PlaybackError,
    PlaybackProgress,
    PlayQueueItem,
    PlayQueueItemType,
    RenderingState,
    SceneProperties,
    Source,
    UserFlow,
    VolumeLevel,
    VolumeMute,
    VolumeState,
)

from homeassistant.components.bang_olufsen.beoremote_halo.models import Icons
from homeassistant.components.bang_olufsen.const import (
    ATTR_FRIENDLY_NAME,
    ATTR_HALO_SERIAL_NUMBER,
    ATTR_ITEM_NUMBER,
    ATTR_MOZART_SERIAL_NUMBER,
    ATTR_TYPE_NUMBER,
    CONF_BEOLINK_JID,
    CONF_BUTTON_ACTION,
    CONF_BUTTON_TITLE,
    CONF_DEFAULT_BUTTON,
    CONF_ENTITY_MAP,
    CONF_HALO,
    CONF_PAGE_TITLE,
    CONF_PAGES,
    CONF_WHEEL_ACTION,
    BangOlufsenSource,
)
from homeassistant.const import (
    CONF_ENTITIES,
    CONF_ENTITY_ID,
    CONF_HOST,
    CONF_ICON,
    CONF_MODEL,
    CONF_NAME,
)
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

# Device models
TEST_MODEL_BALANCE = "Beosound Balance"
TEST_MODEL_CORE = "Beoconnect Core"
TEST_MODEL_THEATRE = "Beosound Theatre"
TEST_MODEL_LEVEL = "Beosound Level"
TEST_MODEL_HALO = "Beoremote Halo"

# Mozart device 1
TEST_FRIENDLY_NAME = "Living room Balance"
TEST_HOST = "192.168.0.1"
TEST_SERIAL_NUMBER = "11111111"
TEST_ITEM_NUMBER = "1111111"
TEST_TYPE_NUMBER = "1111"
TEST_JID_1 = f"{TEST_TYPE_NUMBER}.{TEST_ITEM_NUMBER}.{TEST_SERIAL_NUMBER}@products.bang-olufsen.com"
TEST_MEDIA_PLAYER_ENTITY_ID = "media_player.beosound_balance_11111111"
TEST_NAME = f"{TEST_MODEL_BALANCE}-{TEST_SERIAL_NUMBER}"

TEST_BUTTON_EVENT_ENTITY_ID = f"event.beosound_balance_{TEST_SERIAL_NUMBER}_play_pause"
TEST_PROXIMITY_EVENT_ENTITY_ID = (
    f"event.beosound_balance_{TEST_SERIAL_NUMBER}_proximity"
)


# Mozart device 2
TEST_FRIENDLY_NAME_2 = "Laundry room Core"
TEST_HOST_2 = "192.168.0.2"
TEST_SERIAL_NUMBER_2 = "22222222"
TEST_JID_2 = f"{TEST_TYPE_NUMBER}.{TEST_ITEM_NUMBER}.{TEST_SERIAL_NUMBER_2}@products.bang-olufsen.com"
TEST_MEDIA_PLAYER_ENTITY_ID_2 = f"media_player.beoconnect_core_{TEST_SERIAL_NUMBER_2}"
TEST_NAME_2 = f"{TEST_MODEL_CORE}-{TEST_SERIAL_NUMBER_2}"

# Mozart device 3
TEST_FRIENDLY_NAME_3 = "Lego room Level"
TEST_HOST_3 = "192.168.0.3"
TEST_SERIAL_NUMBER_3 = "33333333"
TEST_JID_3 = f"{TEST_TYPE_NUMBER}.{TEST_ITEM_NUMBER}.{TEST_SERIAL_NUMBER_3}@products.bang-olufsen.com"
TEST_MEDIA_PLAYER_ENTITY_ID_3 = f"media_player.beosound_level_{TEST_SERIAL_NUMBER_3}"
TEST_NAME_3 = f"{TEST_MODEL_LEVEL}-{TEST_SERIAL_NUMBER_3}"

TEST_BATTERY_CHARGING_BINARY_SENSOR_ENTITY_ID = (
    f"binary_sensor.beosound_level_{TEST_SERIAL_NUMBER_3}_battery_charging"
)
TEST_BATTERY_CHARGING_TIME_SENSOR_ENTITY_ID = (
    f"sensor.beosound_level_{TEST_SERIAL_NUMBER_3}_battery_charging_time"
)
TEST_BATTERY_LEVEL_SENSOR_ENTITY_ID = (
    f"sensor.beosound_level_{TEST_SERIAL_NUMBER_3}_battery_level"
)
TEST_BATTERY_PLAYING_TIME_SENSOR_ENTITY_ID = (
    f"sensor.beosound_level_{TEST_SERIAL_NUMBER_3}_battery_playing_time"
)

# Mozart device 4
TEST_FRIENDLY_NAME_4 = "Lounge room Balance"
TEST_JID_4 = f"{TEST_TYPE_NUMBER}.{TEST_ITEM_NUMBER}.44444444@products.bang-olufsen.com"
TEST_MEDIA_PLAYER_ENTITY_ID_4 = "media_player.beosound_balance_44444444"
TEST_HOST_4 = "192.168.0.4"

# Beoremote One
TEST_REMOTE_SERIAL = "55555555"
TEST_REMOTE_SERIAL_PAIRED = f"{TEST_REMOTE_SERIAL}_{TEST_SERIAL_NUMBER}"
TEST_REMOTE_SW_VERSION = "1.0.0"

TEST_REMOTE_KEY_EVENT_ENTITY_ID = "event.beoremote_one_55555555_11111111_control_play"

# Beoremote Halo
TEST_HALO_SERIAL = "66666666"
TEST_HALO_NAME = f"Beoremote Halo-{TEST_HALO_SERIAL}"
TEST_HALO_BATTERY_SENSOR_ENTITY_ID = (
    f"sensor.beoremote_halo_{TEST_HALO_SERIAL}_battery_level"
)
TEST_HALO_BATTERY_CHARGING_BINARY_SENSOR_ENTITY_ID = (
    f"binary_sensor.beoremote_halo_{TEST_HALO_SERIAL}_battery_charging"
)
TEST_HALO_SYSTEM_STATUS_EVENT_ENTITY_ID = (
    f"event.beoremote_halo_{TEST_HALO_SERIAL}_system_status"
)


# Config flow
TEST_HOST_INVALID = "192.168.0"
TEST_HOST_IPV6 = "1111:2222:3333:4444:5555:6666:7777:8888"

TEST_HOSTNAME_ZEROCONF = TEST_NAME.replace(" ", "-") + ".local."
TEST_TYPE_ZEROCONF = "_bangolufsen._tcp.local."
TEST_NAME_ZEROCONF = TEST_NAME.replace(" ", "-") + "." + TEST_TYPE_ZEROCONF

TEST_HALO_HOSTNAME_ZEROCONF = f"BeoremoteHalo-{TEST_HALO_SERIAL}.local"
TEST_HALO_TYPE_ZEROCONF = "_zenith._tcp.local."
TEST_HALO_NAME_ZEROCONF = (
    f"BeoremoteHalo-{TEST_SERIAL_NUMBER}.{TEST_HALO_TYPE_ZEROCONF}"
)

TEST_DATA_USER = {CONF_HOST: TEST_HOST, CONF_MODEL: TEST_MODEL_BALANCE}
TEST_DATA_USER_INVALID = {
    CONF_HOST: TEST_HOST_INVALID,
    CONF_MODEL: TEST_MODEL_BALANCE,
}

TEST_DATA_CREATE_ENTRY = {
    CONF_HOST: TEST_HOST,
    CONF_MODEL: TEST_MODEL_BALANCE,
    CONF_BEOLINK_JID: TEST_JID_1,
    CONF_NAME: TEST_NAME,
}
TEST_DATA_CREATE_ENTRY_2 = {
    CONF_HOST: TEST_HOST_2,
    CONF_MODEL: TEST_MODEL_CORE,
    CONF_BEOLINK_JID: TEST_JID_2,
    CONF_NAME: TEST_NAME_2,
}

TEST_DATA_CREATE_ENTRY_3 = {
    CONF_HOST: TEST_HOST_3,
    CONF_MODEL: TEST_MODEL_LEVEL,
    CONF_BEOLINK_JID: TEST_JID_3,
    CONF_NAME: TEST_NAME_3,
}

TEST_HALO_DATA_CREATE_ENTRY = {
    CONF_HOST: TEST_HOST,
    CONF_MODEL: TEST_MODEL_HALO,
    CONF_BEOLINK_JID: "",
    CONF_NAME: TEST_HALO_NAME,
}

# Halo config flow options
TEST_HALO_PAGE_TITLE = "Test page"
TEST_HALO_PAGE_ENTITIES = [TEST_HALO_BATTERY_SENSOR_ENTITY_ID]
TEST_HALO_DATA_PAGE = {
    CONF_PAGE_TITLE: TEST_HALO_PAGE_TITLE,
    CONF_ENTITIES: TEST_HALO_PAGE_ENTITIES,
}
TEST_HALO_DATA_BUTTON = {
    CONF_BUTTON_TITLE: "Battery",
    CONF_ICON: Icons.ENERGIZE.name,
}
TEST_HALO_DATA_BUTTON_MODIFIED = {
    CONF_BUTTON_TITLE: "Battery :)",
    CONF_ICON: Icons.ALTERNATIVE.name,
}
TEST_HALO_DATA_BUTTON_2 = {
    # String limit of 15
    CONF_BUTTON_TITLE: "Bat. Charging",
    CONF_ICON: Icons.AUTO.name,
}


TEST_HALO_UUID_TARGET = "homeassistant.components.bang_olufsen.config_flow._halo_uuid"

TEST_HALO_CONFIGURATION_ID = "8f1b81fe-2748-11f0-b515-d0abd5978ec0"
TEST_HALO_PAGE_ID = "c45c74b4-3c39-6c87-f858-22b24dc2ad8b"
TEST_HALO_BUTTON_ID = "cf7a7540-fac2-aee2-ad95-1a7f90ac29f1"
TEST_HALO_BUTTON_2_ID = "2ea37900-aaf6-4acd-5ce5-72ad24d7537b"

TEST_HALO_DATA_CONFIGURATION = {
    "configuration": {
        "pages": [
            {
                "title": TEST_HALO_PAGE_TITLE,
                "buttons": [
                    {
                        "title": TEST_HALO_DATA_BUTTON[CONF_BUTTON_TITLE],
                        "content": {"icon": Icons.ENERGIZE.value},
                        "default": False,
                        "id": TEST_HALO_BUTTON_ID,
                    },
                ],
                "id": TEST_HALO_PAGE_ID,
            }
        ],
        "version": "1.0.2",
        "id": TEST_HALO_CONFIGURATION_ID,
    }
}
TEST_HALO_DATA_CONFIGURATION_EMPTY = {
    "configuration": {
        "pages": [],
        "version": "1.0.2",
        "id": TEST_HALO_CONFIGURATION_ID,
    }
}

TEST_HALO_DATA_CONFIGURATION_DEFAULT = {
    "configuration": {
        "pages": [
            {
                "title": TEST_HALO_PAGE_TITLE,
                "buttons": [
                    {
                        "title": TEST_HALO_DATA_BUTTON[CONF_BUTTON_TITLE],
                        "content": {"icon": Icons.ENERGIZE.value},
                        "default": True,
                        "id": TEST_HALO_BUTTON_ID,
                    },
                ],
                "id": TEST_HALO_PAGE_ID,
            }
        ],
        "version": "1.0.2",
        "id": TEST_HALO_CONFIGURATION_ID,
    }
}

TEST_HALO_DATA_CONFIGURATION_2_BUTTONS = {
    "configuration": {
        "pages": [
            {
                "title": TEST_HALO_PAGE_TITLE,
                "buttons": [
                    {
                        "title": TEST_HALO_DATA_BUTTON[CONF_BUTTON_TITLE],
                        "content": {"icon": Icons.ENERGIZE.value},
                        "default": False,
                        "id": TEST_HALO_BUTTON_ID,
                    },
                    {
                        "title": TEST_HALO_DATA_BUTTON_2[CONF_BUTTON_TITLE],
                        "content": {"icon": Icons.AUTO.value},
                        "default": False,
                        "id": TEST_HALO_BUTTON_2_ID,
                    },
                ],
                "id": TEST_HALO_PAGE_ID,
            }
        ],
        "version": "1.0.2",
        "id": TEST_HALO_CONFIGURATION_ID,
    }
}

TEST_HALO_DATA_CONFIGURATION_MODIFIED = {
    "configuration": {
        "pages": [
            {
                "title": TEST_HALO_PAGE_TITLE,
                "buttons": [
                    {
                        "title": TEST_HALO_DATA_BUTTON_MODIFIED[CONF_BUTTON_TITLE],
                        "content": {"icon": Icons.ALTERNATIVE.value},
                        "default": False,
                        "id": TEST_HALO_BUTTON_ID,
                    },
                ],
                "id": TEST_HALO_PAGE_ID,
            }
        ],
        "version": "1.0.2",
        "id": TEST_HALO_CONFIGURATION_ID,
    }
}

TEST_HALO_DATA_CREATE_ENTRY_WITH_CONFIGURATION = {
    CONF_HOST: TEST_HOST,
    CONF_MODEL: TEST_MODEL_HALO,
    CONF_NAME: TEST_HALO_NAME,
    CONF_HALO: TEST_HALO_DATA_CONFIGURATION,
    CONF_ENTITY_MAP: {
        TEST_HALO_BUTTON_ID: {
            CONF_ENTITY_ID: TEST_HALO_BATTERY_SENSOR_ENTITY_ID,
            CONF_BUTTON_ACTION: None,
            CONF_WHEEL_ACTION: None,
        },
    },
}
TEST_HALO_DATA_CREATE_ENTRY_WITH_CONFIGURATION_EMPTY = {
    CONF_HOST: TEST_HOST,
    CONF_MODEL: TEST_MODEL_HALO,
    CONF_NAME: TEST_HALO_NAME,
    CONF_HALO: TEST_HALO_DATA_CONFIGURATION_EMPTY,
    CONF_ENTITY_MAP: {},
}
TEST_HALO_DATA_CREATE_ENTRY_WITH_CONFIGURATION_DEFAULT = {
    CONF_HOST: TEST_HOST,
    CONF_MODEL: TEST_MODEL_HALO,
    CONF_NAME: TEST_HALO_NAME,
    CONF_HALO: TEST_HALO_DATA_CONFIGURATION_DEFAULT,
    CONF_ENTITY_MAP: {
        TEST_HALO_BUTTON_ID: {
            CONF_ENTITY_ID: TEST_HALO_BATTERY_SENSOR_ENTITY_ID,
            CONF_BUTTON_ACTION: None,
            CONF_WHEEL_ACTION: None,
        },
    },
}
TEST_HALO_DATA_CREATE_ENTRY_WITH_CONFIGURATION_2_BUTTONS = {
    CONF_HOST: TEST_HOST,
    CONF_MODEL: TEST_MODEL_HALO,
    CONF_NAME: TEST_HALO_NAME,
    CONF_HALO: TEST_HALO_DATA_CONFIGURATION_2_BUTTONS,
    CONF_ENTITY_MAP: {
        TEST_HALO_BUTTON_ID: {
            CONF_ENTITY_ID: TEST_HALO_BATTERY_SENSOR_ENTITY_ID,
            CONF_BUTTON_ACTION: None,
            CONF_WHEEL_ACTION: None,
        },
        TEST_HALO_BUTTON_2_ID: {
            CONF_ENTITY_ID: TEST_HALO_BATTERY_CHARGING_BINARY_SENSOR_ENTITY_ID,
            CONF_BUTTON_ACTION: None,
            CONF_WHEEL_ACTION: None,
        },
    },
}
TEST_HALO_DATA_CREATE_ENTRY_WITH_CONFIGURATION_MODIFIED = {
    CONF_HOST: TEST_HOST,
    CONF_MODEL: TEST_MODEL_HALO,
    CONF_NAME: TEST_HALO_NAME,
    CONF_HALO: TEST_HALO_DATA_CONFIGURATION_MODIFIED,
    CONF_ENTITY_MAP: {
        TEST_HALO_BUTTON_ID: {
            CONF_ENTITY_ID: TEST_HALO_BATTERY_SENSOR_ENTITY_ID,
            CONF_BUTTON_ACTION: None,
            CONF_WHEEL_ACTION: None,
        }
    },
}

TEST_HALO_PAGE = f"{TEST_HALO_PAGE_TITLE} - ({TEST_HALO_PAGE_ID})"
TEST_HALO_DATA_SELECT_PAGE = {CONF_PAGES: TEST_HALO_PAGE}
TEST_HALO_DATA_SELECT_PAGES = {CONF_PAGES: [TEST_HALO_PAGE]}
TEST_HALO_DATA_PAGE_BUTTONS = {
    CONF_PAGE_TITLE: TEST_HALO_PAGE_TITLE,
    CONF_ENTITIES: [TEST_HALO_BATTERY_SENSOR_ENTITY_ID],
}
TEST_HALO_DATA_PAGE_2_BUTTONS = {
    CONF_PAGE_TITLE: TEST_HALO_PAGE_TITLE,
    CONF_ENTITIES: [
        TEST_HALO_BATTERY_SENSOR_ENTITY_ID,
        TEST_HALO_BATTERY_CHARGING_BINARY_SENSOR_ENTITY_ID,
    ],
}
TEST_HALO_BUTTON = f"{TEST_HALO_PAGE_TITLE}-{TEST_HALO_DATA_BUTTON[CONF_BUTTON_TITLE]} ({TEST_HALO_BUTTON_ID})"
TEST_HALO_DATA_SELECT_DEFAULT = {CONF_DEFAULT_BUTTON: TEST_HALO_BUTTON}

TEST_DATA_ZEROCONF = ZeroconfServiceInfo(
    ip_address=IPv4Address(TEST_HOST),
    ip_addresses=[IPv4Address(TEST_HOST)],
    port=80,
    hostname=TEST_HOSTNAME_ZEROCONF,
    type=TEST_TYPE_ZEROCONF,
    name=TEST_NAME_ZEROCONF,
    properties={
        ATTR_FRIENDLY_NAME: TEST_FRIENDLY_NAME,
        ATTR_MOZART_SERIAL_NUMBER: TEST_SERIAL_NUMBER,
        ATTR_TYPE_NUMBER: TEST_TYPE_NUMBER,
        ATTR_ITEM_NUMBER: TEST_ITEM_NUMBER,
    },
)

TEST_DATA_ZEROCONF_NOT_MOZART = ZeroconfServiceInfo(
    ip_address=IPv4Address(TEST_HOST),
    ip_addresses=[IPv4Address(TEST_HOST)],
    port=80,
    hostname=TEST_HOSTNAME_ZEROCONF,
    type=TEST_TYPE_ZEROCONF,
    name=TEST_NAME_ZEROCONF,
    properties={ATTR_MOZART_SERIAL_NUMBER: TEST_SERIAL_NUMBER},
)

TEST_DATA_ZEROCONF_IPV6 = ZeroconfServiceInfo(
    ip_address=IPv6Address(TEST_HOST_IPV6),
    ip_addresses=[IPv6Address(TEST_HOST_IPV6)],
    port=80,
    hostname=TEST_HOSTNAME_ZEROCONF,
    type=TEST_TYPE_ZEROCONF,
    name=TEST_NAME_ZEROCONF,
    properties={
        ATTR_FRIENDLY_NAME: TEST_FRIENDLY_NAME,
        ATTR_MOZART_SERIAL_NUMBER: TEST_SERIAL_NUMBER,
        ATTR_TYPE_NUMBER: TEST_TYPE_NUMBER,
        ATTR_ITEM_NUMBER: TEST_ITEM_NUMBER,
    },
)

TEST_HALO_DATA_ZEROCONF = ZeroconfServiceInfo(
    ip_address=IPv4Address(TEST_HOST),
    ip_addresses=[IPv4Address(TEST_HOST)],
    port=80,
    hostname=TEST_HALO_HOSTNAME_ZEROCONF,
    type=TEST_HALO_TYPE_ZEROCONF,
    name=TEST_HALO_NAME_ZEROCONF,
    properties={
        ATTR_HALO_SERIAL_NUMBER: TEST_HALO_SERIAL,
        CONF_NAME: TEST_MODEL_HALO,
    },
)

TEST_SOURCE = Source(
    name="Tidal", id="tidal", is_seekable=True, is_enabled=True, is_playable=True
)
TEST_AUDIO_SOURCES = [TEST_SOURCE.name, BangOlufsenSource.LINE_IN.name]
TEST_VIDEO_SOURCES = ["HDMI A"]
TEST_SOURCES = TEST_AUDIO_SOURCES + TEST_VIDEO_SOURCES
TEST_FALLBACK_SOURCES = [
    "Audio Streamer",
    "Bluetooth",
    "Spotify Connect",
    "Line-In",
    "Optical",
    "B&O Radio",
    "Deezer",
    "Tidal Connect",
]
TEST_PLAYBACK_METADATA = PlaybackContentMetadata(
    album_name="Test album",
    artist_name="Test artist",
    organization="Test organization",
    title="Test title",
    total_duration_seconds=123,
    track=1,
)
TEST_PLAYBACK_ERROR = PlaybackError(error="Test error")
TEST_PLAYBACK_PROGRESS = PlaybackProgress(progress=123)
TEST_PLAYBACK_STATE_PAUSED = RenderingState(value="paused")
TEST_PLAYBACK_STATE_PLAYING = RenderingState(value="started")
TEST_VOLUME = VolumeState(level=VolumeLevel(level=40))
TEST_VOLUME_HOME_ASSISTANT_FORMAT = 0.4
TEST_PLAYBACK_STATE_TURN_OFF = RenderingState(value="stopped")
TEST_VOLUME_MUTED = VolumeState(
    muted=VolumeMute(muted=True), level=VolumeLevel(level=40)
)
TEST_VOLUME_MUTED_HOME_ASSISTANT_FORMAT = True
TEST_SEEK_POSITION_HOME_ASSISTANT_FORMAT = 10.0
TEST_SEEK_POSITION = 10000
TEST_OVERLAY_INVALID_OFFSET_VOLUME_TTS = OverlayPlayRequest(
    text_to_speech=OverlayPlayRequestTextToSpeechTextToSpeech(
        lang="da-dk", text="Dette er en test"
    )
)
TEST_OVERLAY_OFFSET_VOLUME_TTS = OverlayPlayRequest(
    text_to_speech=OverlayPlayRequestTextToSpeechTextToSpeech(
        lang="en-us", text="This is a test"
    ),
    volume_absolute=60,
)
TEST_RADIO_STATION = SceneProperties(
    action_list=[
        Action(
            type="radio",
            radio_station_id="1234567890123456",
        )
    ]
)
TEST_DEEZER_FLOW = UserFlow(user_id="123")
TEST_DEEZER_PLAYLIST = PlayQueueItem(
    provider=PlayQueueItemType(value="deezer"),
    start_now_from_position=123,
    type="playlist",
    uri="playlist:1234567890",
)
TEST_DEEZER_TRACK = PlayQueueItem(
    provider=PlayQueueItemType(value="deezer"),
    start_now_from_position=0,
    type="track",
    uri="1234567890",
)

# codespell can't see the escaped ', so it thinks the word is misspelled
TEST_DEEZER_INVALID_FLOW = ApiException(
    status=400,
    reason="Bad Request",
    http_resp=Mock(
        status=400,
        reason="Bad Request",
        data='{"message": "Couldn\'t start user flow for me"}',  # codespell:ignore
    ),
)
TEST_SOUND_MODE = 123
TEST_SOUND_MODE_2 = 234
TEST_SOUND_MODE_NAME = "Test Listening Mode"
TEST_ACTIVE_SOUND_MODE_NAME = f"{TEST_SOUND_MODE_NAME} ({TEST_SOUND_MODE})"
TEST_ACTIVE_SOUND_MODE_NAME_2 = f"{TEST_SOUND_MODE_NAME} ({TEST_SOUND_MODE_2})"
TEST_LISTENING_MODE_REF = ListeningModeRef(href="", id=TEST_SOUND_MODE_2)
TEST_SOUND_MODES = [
    TEST_ACTIVE_SOUND_MODE_NAME,
    TEST_ACTIVE_SOUND_MODE_NAME_2,
    f"{TEST_SOUND_MODE_NAME} 2 (345)",
]
