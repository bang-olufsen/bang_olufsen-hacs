"""The Bang & Olufsen integration."""
from __future__ import annotations

import logging

from mozart_api.mozart_client import MozartClient

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_NAME, Platform
from homeassistant.core import HomeAssistant

from .binary_sensor import (
    BangOlufsenBinarySensor,
    BangOlufsenBinarySensorBatteryCharging,
    BangOlufsenBinarySensorProximity,
)
from .button import BangOlufsenButtonFavourite
from .const import (
    DOMAIN,
    HASS_BINARY_SENSORS,
    HASS_CONTROLLER,
    HASS_COORDINATOR,
    HASS_FAVOURITES,
    HASS_MEDIA_PLAYER,
    HASS_NUMBERS,
    HASS_SELECTS,
    HASS_SENSORS,
    HASS_SWITCHES,
    HASS_TEXT,
    SUPPORTS_PROXIMITY_SENSOR,
)
from .controller import BangOlufsenController
from .coordinator import BangOlufsenCoordinator
from .media_player import BangOlufsenMediaPlayer
from .number import BangOlufsenNumberBass, BangOlufsenNumberTreble
from .select import BangOlufsenSelectSoundMode
from .sensor import (
    BangOlufsenSensorBatteryChargingTime,
    BangOlufsenSensorBatteryLevel,
    BangOlufsenSensorBatteryPlayingTime,
)
from .switch import BangOlufsenSwitchLoudness
from .text import BangOlufsenTextMediaId

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.MEDIA_PLAYER,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TEXT,
    Platform.SELECT,
]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Check if there are available options.
    if entry.options:
        entry.data = entry.options

    # If connection can't be made abort.
    if not await init_entities(hass, entry):
        return False

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

    client = MozartClient(host=entry.data[CONF_HOST])
    supports_battery = False
    model = entry.data[CONF_MODEL]

    # Check connection and try to initialize it.
    if not (
        battery_state := client.get_battery_state(
            async_req=True, _request_timeout=3
        ).get()
    ):
        _LOGGER.error("Unable to connect to %s", entry.data[CONF_NAME])
        return False

    # Get whether or not the device has a battery.
    if battery_state.battery_level > 0:
        supports_battery = True

    # Create the coordinator.
    coordinator = BangOlufsenCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    # Create the Binary Sensor entities.
    binary_sensors: list[BangOlufsenBinarySensor] = []

    if supports_battery:
        binary_sensors.append(BangOlufsenBinarySensorBatteryCharging(entry))

    # Check if device supports proxmity detection.
    if model in SUPPORTS_PROXIMITY_SENSOR:
        binary_sensors.append(BangOlufsenBinarySensorProximity(entry))

    # Create the Number entities.
    numbers = [BangOlufsenNumberBass(entry), BangOlufsenNumberTreble(entry)]

    # Get available favourites.
    favourites = client.get_presets(async_req=True).get()

    # Create the favourites Button entities.
    favourite_buttons = []

    for favourite_id in favourites:
        favourite_buttons.append(
            BangOlufsenButtonFavourite(entry, coordinator, favourites[favourite_id])
        )

    # Create the Sensor entities.
    sensors = []

    if supports_battery:
        sensors.extend(
            [
                BangOlufsenSensorBatteryChargingTime(entry),
                BangOlufsenSensorBatteryLevel(entry),
                BangOlufsenSensorBatteryPlayingTime(entry),
            ]
        )

    # Create the Switch entities.
    switches = [BangOlufsenSwitchLoudness(entry)]

    # Create the Text entities.
    texts = [BangOlufsenTextMediaId(entry)]

    # Create the Select entities.
    selects = []

    # Create the sound mode select entity if supported
    listening_modes = client.get_listening_mode_set(async_req=True).get()
    if len(listening_modes) > 0:
        selects.append(BangOlufsenSelectSoundMode(entry))

    # Create the Media Player entity.
    media_player = BangOlufsenMediaPlayer(entry, coordinator)

    # Handle WebSocket notifications
    controller = BangOlufsenController(hass, entry)

    # Add the created entities
    hass.data[DOMAIN][entry.unique_id] = {
        HASS_BINARY_SENSORS: binary_sensors,
        HASS_CONTROLLER: controller,
        HASS_COORDINATOR: coordinator,
        HASS_MEDIA_PLAYER: media_player,
        HASS_NUMBERS: numbers,
        HASS_FAVOURITES: favourite_buttons,
        HASS_SENSORS: sensors,
        HASS_SWITCHES: switches,
        HASS_SELECTS: selects,
        HASS_TEXT: texts,
    }

    return True
