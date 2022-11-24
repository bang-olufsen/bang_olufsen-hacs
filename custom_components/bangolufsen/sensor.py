"""Sensor entities for the Bang & Olufsen integration."""
from __future__ import annotations

from datetime import timedelta

from mozart_api.models import BatteryState

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.dt import utcnow

from .const import (
    BATTERY_NOTIFICATION,
    CONNECTION_STATUS,
    DOMAIN,
    HASS_SENSORS,
    BangOlufsenVariables,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sensor entities from config entry."""
    entities = []

    # Add sensor entities.
    for sensor in hass.data[DOMAIN][config_entry.unique_id][HASS_SENSORS]:
        entities.append(sensor)

    async_add_entities(new_entities=entities, update_before_add=True)


class BangOlufsenSensor(BangOlufsenVariables, SensorEntity):
    """Base Sensor class."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Init the Sensor."""
        super().__init__(entry)

        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_available = True
        self._attr_should_poll = False
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, self._unique_id)})

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        connection_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{self._unique_id}_{CONNECTION_STATUS}",
            self._update_connection_state,
        )

        self._dispatchers.append(connection_dispatcher)

    async def async_will_remove_from_hass(self) -> None:
        """Turn off the dispatchers."""
        for dispatcher in self._dispatchers:
            dispatcher()

    async def _update_connection_state(self, connection_state: bool) -> None:
        """Update entity connection state."""
        self._attr_available = connection_state

        self.async_write_ha_state()


class BangOlufsenSensorBatteryLevel(BangOlufsenSensor):
    """Battery level Sensor."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Init the battery level Sensor."""
        super().__init__(entry)

        self._attr_name = f"{self._name} Battery level"
        self._attr_unique_id = f"{self._unique_id}-battery-level"
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_icon = "mdi:battery"

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        sensor_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{self._unique_id}_{BATTERY_NOTIFICATION}",
            self._update_battery,
        )

        connection_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{self._unique_id}_{CONNECTION_STATUS}",
            self._update_connection_state,
        )

        self._dispatchers.append(sensor_dispatcher)
        self._dispatchers.append(connection_dispatcher)

    async def _update_battery(self, data: BatteryState) -> None:
        """Update sensor value."""
        self._battery = data
        self._attr_native_value = self._battery.battery_level
        self.async_write_ha_state()


class BangOlufsenSensorBatteryChargingTime(BangOlufsenSensor):
    """Battery charging time Sensor."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Init the battery charging time Sensor."""
        super().__init__(entry)

        self._attr_name = f"{self._name} Battery charging time"
        self._attr_unique_id = f"{self._unique_id}-battery-charging-time"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_icon = "mdi:battery-arrow-up"
        self._attr_entity_registry_enabled_default = False

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        sensor_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{self._unique_id}_{BATTERY_NOTIFICATION}",
            self._update_battery,
        )

        connection_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{self._unique_id}_{CONNECTION_STATUS}",
            self._update_connection_state,
        )

        self._dispatchers.append(sensor_dispatcher)
        self._dispatchers.append(connection_dispatcher)

    async def _update_battery(self, data: BatteryState) -> None:
        """Update sensor value."""
        self._battery = data

        self._attr_available = True

        current_time = utcnow()
        time_to_add = timedelta(minutes=self._battery.remaining_charging_time_minutes)

        self._attr_native_value = current_time + time_to_add

        self.async_write_ha_state()


class BangOlufsenSensorBatteryPlayingTime(BangOlufsenSensor):
    """Battery playing time Sensor."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Init the battery playing time Sensor."""
        super().__init__(entry)

        self._attr_name = f"{self._name} Battery playing time"
        self._attr_unique_id = f"{self._unique_id}-battery-playing-time"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_icon = "mdi:battery-arrow-down"
        self._attr_entity_registry_enabled_default = False

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        sensor_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{self._unique_id}_{BATTERY_NOTIFICATION}",
            self._update_battery,
        )

        connection_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{self._unique_id}_{CONNECTION_STATUS}",
            self._update_connection_state,
        )

        self._dispatchers.append(sensor_dispatcher)
        self._dispatchers.append(connection_dispatcher)

    async def _update_battery(self, data: BatteryState) -> None:
        """Update sensor value."""
        self._battery = data

        self._attr_available = True

        current_time = utcnow()
        time_to_add = timedelta(minutes=self._battery.remaining_playing_time_minutes)
        self._attr_native_value = current_time + time_to_add

        self.async_write_ha_state()
