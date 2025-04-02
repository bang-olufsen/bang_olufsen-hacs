"""Binary Sensor entities for the Bang & Olufsen integration."""

from __future__ import annotations

from mozart_api.models import BatteryState

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HaloConfigEntry, MozartConfigEntry
from .beoremote_halo.models import PowerEvent, PowerEventState
from .const import CONNECTION_STATUS, WebsocketNotification
from .entity import HaloEntity, MozartEntity
from .util import is_halo


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Binary Sensor entities from config entry."""
    entities: list[BangOlufsenBinarySensor] = []

    if is_halo(config_entry):
        entities.extend(await _get_halo_entities(config_entry))
    else:
        entities.extend(await _get_mozart_entities(config_entry))

    async_add_entities(new_entities=entities)


class BangOlufsenBinarySensor(BinarySensorEntity):
    """Base Binary Sensor class."""

    _attr_is_on = False


# Mozart entities
class MozartBinarySensor(MozartEntity, BangOlufsenBinarySensor):
    """Base Mozart Sensor class."""

    def __init__(self, config_entry: MozartConfigEntry) -> None:
        """Init the Binary Sensor."""
        super().__init__(config_entry)


async def _get_mozart_entities(
    config_entry: MozartConfigEntry,
) -> list[MozartBinarySensor]:
    """Get Mozart Sensor entities from config entry."""
    entities: list[MozartBinarySensor] = []

    # Check if device has a battery
    battery_state = await config_entry.runtime_data.client.get_battery_state()

    if battery_state.battery_level and battery_state.battery_level > 0:
        entities.append(MozartBinarySensorBatteryCharging(config_entry))

    return entities


class MozartBinarySensorBatteryCharging(MozartBinarySensor):
    """Battery charging Binary Sensor."""

    _attr_translation_key = "battery_charging"

    def __init__(self, config_entry: MozartConfigEntry) -> None:
        """Init the battery charging Binary Sensor."""
        super().__init__(config_entry)

        self._attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING
        self._attr_unique_id = f"{self._unique_id}_battery_charging"

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{CONNECTION_STATUS}",
                self._async_update_connection_state,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{WebsocketNotification.BATTERY}",
                self._update_battery_charging,
            )
        )

    async def _update_battery_charging(self, data: BatteryState) -> None:
        """Update battery charging."""
        self._attr_is_on = bool(data.is_charging)
        self.async_write_ha_state()


# Halo entities


class HaloBinarySensor(HaloEntity, BangOlufsenBinarySensor):
    """Base Halo Binary Sensor class."""

    def __init__(self, config_entry: HaloConfigEntry) -> None:
        """Init the Sensor."""
        super().__init__(config_entry)


async def _get_halo_entities(
    config_entry: HaloConfigEntry,
) -> list[HaloBinarySensor]:
    """Get Halo Binary Sensor entities from config entry."""
    return [HaloBinarySensorBatteryCharging(config_entry)]


class HaloBinarySensorBatteryCharging(HaloBinarySensor):
    """Battery charging Binary Sensor."""

    _attr_translation_key = "halo_battery_charging"

    def __init__(self, config_entry: HaloConfigEntry) -> None:
        """Init the battery charging Binary Sensor."""
        super().__init__(config_entry)

        self._attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING
        self._attr_unique_id = f"{self._unique_id}_battery_charging"

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{CONNECTION_STATUS}",
                self._async_update_connection_state,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{WebsocketNotification.HALO_POWER}",
                self._update_battery_charging,
            )
        )

    async def _update_battery_charging(self, data: PowerEvent) -> None:
        """Update battery charging."""
        self._attr_is_on = data.state == PowerEventState.CHARGING
        self.async_write_ha_state()
