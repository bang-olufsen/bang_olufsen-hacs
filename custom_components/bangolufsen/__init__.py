"""The Bang & Olufsen integration."""
from __future__ import annotations

import logging
from multiprocessing.pool import ApplyResult
from typing import cast

from mozart_api.models import (
    BatteryState,
    BeolinkPeer,
    HomeControlUri,
    ListeningMode,
    Preset,
    Scene,
)
from mozart_api.mozart_client import MozartClient
from urllib3.exceptions import MaxRetryError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MODEL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import async_call_later

from .binary_sensor import (
    BangOlufsenBinarySensor,
    BangOlufsenBinarySensorBatteryCharging,
    BangOlufsenBinarySensorProximity,
)
from .button import BangOlufsenButtonFavourite
from .const import (
    DOMAIN,
    ENTITY_ENUM,
    MODEL_ENUM,
    SUPPORT_ENUM,
    WEBSOCKET_CONNECTION_DELAY,
)
from .coordinator import BangOlufsenCoordinator
from .media_player import BangOlufsenMediaPlayer
from .number import BangOlufsenNumber, BangOlufsenNumberBass, BangOlufsenNumberTreble
from .select import (
    BangOlufsenSelect,
    BangOlufsenSelectListeningPosition,
    BangOlufsenSelectSoundMode,
)
from .sensor import (
    BangOlufsenSensor,
    BangOlufsenSensorBatteryChargingTime,
    BangOlufsenSensorBatteryLevel,
    BangOlufsenSensorBatteryPlayingTime,
    BangOlufsenSensorInputSignal,
    BangOlufsenSensorMediaId,
)
from .switch import BangOlufsenSwitch, BangOlufsenSwitchLoudness
from .text import (
    BangOlufsenText,
    BangOlufsenTextFriendlyName,
    BangOlufsenTextHomeControlUri,
)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TEXT,
    Platform.MEDIA_PLAYER,
    Platform.SELECT,
]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    # Check if there are available options.
    if entry.options:
        entry.data = entry.options

    # Ensure that a unique id is available
    if not entry.unique_id:
        raise ConfigEntryError("Can't retrieve unique id from config entry. Aborting")

    # Create device in order to ensure entity platforms (button, binary_sensor)
    # have device name before the primary (media_player) is initialized
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.unique_id)},
        name=entry.title,
        model=entry.data[CONF_MODEL],
    )

    # If connection can't be made abort.
    if not await init_entities(hass, entry):
        raise ConfigEntryNotReady(f"Unable to connect to {entry.title}")

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.unique_id)

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def init_entities(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Initialise the supported entities of the device."""
    client = MozartClient(
        host=entry.data[CONF_HOST], urllib3_logging_level=logging.ERROR
    )
    supports_battery = False
    model = entry.data[CONF_MODEL]

    # Check connection and try to initialize it.
    try:
        battery_state = cast(
            ApplyResult[BatteryState],
            client.get_battery_state(
                async_req=True,
                _request_timeout=3,
            ),
        ).get()
    except MaxRetryError:
        return False

    # Get whether or not the device has a battery.
    if battery_state.battery_level and battery_state.battery_level > 0:
        supports_battery = True

    # Create the coordinator.
    coordinator = BangOlufsenCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    # Create the Binary Sensor entities.
    binary_sensors: list[BangOlufsenBinarySensor] = []

    if supports_battery:
        binary_sensors.append(BangOlufsenBinarySensorBatteryCharging(entry))

    # Check if device supports proximity detection.
    if model in SUPPORT_ENUM.PROXIMITY_SENSOR.value:
        binary_sensors.append(BangOlufsenBinarySensorProximity(entry))

    # Create the Number entities.
    numbers: list[BangOlufsenNumber] = [
        BangOlufsenNumberBass(entry),
        BangOlufsenNumberTreble(entry),
    ]

    # Get available favourites.
    favourites = cast(
        ApplyResult[dict[str, Preset]], client.get_presets(async_req=True)
    ).get()

    # Create the favourites Button entities.
    favourite_buttons: list[BangOlufsenButtonFavourite] = []

    for favourite_id in favourites:
        favourite_buttons.append(
            BangOlufsenButtonFavourite(entry, coordinator, favourites[favourite_id])
        )

    # Create the Sensor entities.
    sensors: list[BangOlufsenSensor] = [
        BangOlufsenSensorInputSignal(entry),
        BangOlufsenSensorMediaId(entry),
    ]

    if supports_battery:
        sensors.extend(
            [
                BangOlufsenSensorBatteryChargingTime(entry),
                BangOlufsenSensorBatteryLevel(entry),
                BangOlufsenSensorBatteryPlayingTime(entry),
            ]
        )

    # Create the Switch entities.
    switches: list[BangOlufsenSwitch] = [BangOlufsenSwitchLoudness(entry)]

    # Create the Text entities.
    beolink_self = cast(
        ApplyResult[BeolinkPeer], client.get_beolink_self(async_req=True)
    ).get()

    texts: list[BangOlufsenText] = [
        BangOlufsenTextFriendlyName(entry, beolink_self.friendly_name),
    ]

    # Add the Home Control URI entity if the device supports it
    if model in SUPPORT_ENUM.HOME_CONTROL.value:
        home_control = cast(
            ApplyResult[HomeControlUri],
            client.get_remote_home_control_uri(async_req=True),
        ).get()

        texts.append(BangOlufsenTextHomeControlUri(entry, home_control.uri))

    # Create the Select entities.
    selects: list[BangOlufsenSelect] = []

    # Create the listening position Select entity if supported
    scenes = cast(
        ApplyResult[dict[str, Scene]], client.get_all_scenes(async_req=True)
    ).get()

    # Listening positions
    for scene_key in scenes:
        scene = scenes[scene_key]

        if scene.tags is not None and "listeningposition" in scene.tags:
            selects.append(BangOlufsenSelectListeningPosition(entry))
            break

    # Create the sound mode select entity if supported
    # Currently the Balance does not expose any useful Sound Modes and should be excluded
    if model != MODEL_ENUM.BEOSOUND_BALANCE:
        listening_modes = cast(
            ApplyResult[list[ListeningMode]],
            client.get_listening_mode_set(async_req=True),
        ).get()
        if len(listening_modes) > 0:
            selects.append(BangOlufsenSelectSoundMode(entry))

    # Create the Media Player entity.
    media_player = BangOlufsenMediaPlayer(entry)

    # Add the created entities
    hass.data[DOMAIN][entry.unique_id] = {
        ENTITY_ENUM.BINARY_SENSORS: binary_sensors,
        ENTITY_ENUM.COORDINATOR: coordinator,
        ENTITY_ENUM.MEDIA_PLAYER: media_player,
        ENTITY_ENUM.NUMBERS: numbers,
        ENTITY_ENUM.FAVOURITES: favourite_buttons,
        ENTITY_ENUM.SENSORS: sensors,
        ENTITY_ENUM.SWITCHES: switches,
        ENTITY_ENUM.SELECTS: selects,
        ENTITY_ENUM.TEXT: texts,
    }
    # Start the WebSocket listener with a delay to allow for entity and dispatcher listener creation
    async_call_later(hass, WEBSOCKET_CONNECTION_DELAY, coordinator.connect_websocket)

    return True
