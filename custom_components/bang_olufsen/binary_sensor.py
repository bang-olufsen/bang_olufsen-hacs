"""Binary Sensor entities for the Bang & Olufsen integration."""

from __future__ import annotations

from mozart_api.models import BatteryState

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BangOlufsenConfigEntry, set_platform_initialized
from .const import CONNECTION_STATUS, WebsocketNotification
from .entity import BangOlufsenEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BangOlufsenConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Binary Sensor entities from config entry."""
    entities: list[BangOlufsenBinarySensor] = []

    # Check if device has a battery
    battery_state = await config_entry.runtime_data.client.get_battery_state()

    if battery_state.battery_level and battery_state.battery_level > 0:
        entities.append(BangOlufsenBinarySensorBatteryCharging(config_entry))

    async_add_entities(new_entities=entities)

    set_platform_initialized(config_entry.runtime_data)


class BangOlufsenBinarySensor(BangOlufsenEntity, BinarySensorEntity):
    """Base Binary Sensor class."""

    def __init__(self, config_entry: BangOlufsenConfigEntry) -> None:
        """Init the Binary Sensor."""
        super().__init__(config_entry)

        self._attr_is_on = False


class BangOlufsenBinarySensorBatteryCharging(BangOlufsenBinarySensor):
    """Battery charging Binary Sensor."""

    _attr_translation_key = "battery_charging"

    def __init__(self, config_entry: BangOlufsenConfigEntry) -> None:
        """Init the battery charging Binary Sensor."""
        super().__init__(config_entry)

        self._attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING
        self._attr_unique_id = f"{self._unique_id}-battery-charging"

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
        self._attr_is_on = data.is_charging
        self.async_write_ha_state()
