"""The Bang & Olufsen Mozart integration."""
from __future__ import annotations

import logging

from mozart_api.mozart_client import MozartClient

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_NAME, Platform
from homeassistant.core import HomeAssistant

from .binary_sensor import (
    MozartBinarySensor,
    MozartBinarySensorBatteryCharging,
    MozartBinarySensorProximity,
)
from .button import MozartButtonPreset
from .const import (
    HASS_BINARY_SENSORS,
    HASS_CONTROLLER,
    HASS_COORDINATOR,
    HASS_MEDIA_PLAYER,
    HASS_NUMBERS,
    HASS_PRESETS,
    HASS_SENSORS,
    HASS_SWITCHES,
    MOZART_DOMAIN,
    SUPPORTS_PROXIMITY_SENSOR,
)
from .controller import MozartController
from .coordinator import MozartCoordinator
from .media_player import MozartMediaPlayer
from .number import MozartNumberBass, MozartNumberTreble
from .sensor import (
    MozartSensorBatteryChargingTime,
    MozartSensorBatteryLevel,
    MozartSensorBatteryPlayingTime,
)
from .switch import MozartSwitchLoudness

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.MEDIA_PLAYER,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up mozart from a config entry."""
    hass.data.setdefault(MOZART_DOMAIN, {})

    # Check if there are available options.
    if entry.options:
        entry.data = entry.options

    # If connection can't be made abort.
    if not await init_entities(hass, entry):
        return False

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[MOZART_DOMAIN].pop(entry.unique_id)

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def init_entities(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Initialise the supported entities of the device."""

    mozart_client = MozartClient(host=entry.data[CONF_HOST])
    supports_battery = False
    model = entry.data[CONF_MODEL]

    # Check connection and try to initialize it.
    if not (
        battery_state := mozart_client.get_battery_state(
            async_req=True, _request_timeout=5
        ).get()
    ):
        _LOGGER.error("Unable to connect to %s", entry.data[CONF_NAME])
        return False

    # Get whether or not the device has a battery.
    if battery_state.battery_level > 0 and battery_state.is_charging is True:
        supports_battery = True

    # Create the Mozart coordinator.
    mozart_coordinator = MozartCoordinator(hass, entry)
    await mozart_coordinator.async_config_entry_first_refresh()

    # Create the Mozart binary sensors.
    mozart_binary_sensors: list[MozartBinarySensor] = []

    if supports_battery:
        mozart_binary_sensors.append(MozartBinarySensorBatteryCharging(entry))

    # Check if device supports proxmity detection
    if model in SUPPORTS_PROXIMITY_SENSOR:
        mozart_binary_sensors.append(MozartBinarySensorProximity(entry))

    # Create the Mozart options numbers.
    mozart_numbers = [MozartNumberBass(entry), MozartNumberTreble(entry)]

    # Get available presets.
    presets = mozart_client.get_presets(async_req=True).get()

    # Create the Mozart preset buttons
    mozart_presets = []

    for preset_id in presets:
        mozart_presets.append(
            MozartButtonPreset(entry, mozart_coordinator, presets[preset_id])
        )

    # Create the Mozart sensors.
    mozart_sensors = []

    if supports_battery:
        mozart_sensors.extend(
            [
                MozartSensorBatteryChargingTime(entry),
                MozartSensorBatteryLevel(entry),
                MozartSensorBatteryPlayingTime(entry),
            ]
        )

    # Create the Mozart options switches.
    mozart_switches = [MozartSwitchLoudness(entry)]

    # Create a Mozart media_player.
    mozart_media_player = MozartMediaPlayer(entry, mozart_coordinator)

    # Initialize the notification listener and remote listener if a remote is paired.
    # The listener is "turned on" in "async_added_to_hass" in media_player.py
    mozart_controller = MozartController(hass, entry)

    # Add the created entities
    hass.data[MOZART_DOMAIN][entry.unique_id] = {
        HASS_BINARY_SENSORS: mozart_binary_sensors,
        HASS_CONTROLLER: mozart_controller,
        HASS_COORDINATOR: mozart_coordinator,
        HASS_MEDIA_PLAYER: mozart_media_player,
        HASS_NUMBERS: mozart_numbers,
        HASS_PRESETS: mozart_presets,
        HASS_SENSORS: mozart_sensors,
        HASS_SWITCHES: mozart_switches,
    }

    return True
