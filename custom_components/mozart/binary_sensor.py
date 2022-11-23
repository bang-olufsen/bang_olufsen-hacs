"""Binary sensor entities for the Bang & Olufsen Mozart integration."""
from __future__ import annotations

from mozart_api.models import BatteryState, WebsocketNotificationTag

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    BATTERY_NOTIFICATION,
    CONNECTION_STATUS,
    HASS_BINARY_SENSORS,
    MOZART_DOMAIN,
    NOTIFICATION_NOTIFICATION_PROXIMITY,
    MozartVariables,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a Mozart binary_sensor entity from config entry."""
    entities = []
    configuration = hass.data[MOZART_DOMAIN][config_entry.unique_id]

    # Add regular binary sensors
    for binary_sensor in configuration[HASS_BINARY_SENSORS]:
        entities.append(binary_sensor)

    async_add_entities(new_entities=entities, update_before_add=True)


class MozartBinarySensor(MozartVariables, BinarySensorEntity):
    """Binary sensor for Mozart settings."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Init the Mozart binary sensor."""
        super().__init__(entry)

        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_available = True
        self._attr_should_poll = False
        self._attr_device_info = DeviceInfo(
            identifiers={(MOZART_DOMAIN, self._unique_id)}
        )

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


class MozartBinarySensorBatteryCharging(MozartBinarySensor):
    """Battery charging binary sensor for Mozart."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Init the battery charging binary sensor."""
        super().__init__(entry)

        self._attr_name = f"{self._name} Battery charging"
        self._attr_unique_id = f"{self._unique_id}-battery-charging"
        self._attr_icon = "mdi:battery-charging"
        self._attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        binary_sensor_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{self._unique_id}_{BATTERY_NOTIFICATION}",
            self._update_battery_charging,
        )

        connection_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{self._unique_id}_{CONNECTION_STATUS}",
            self._update_connection_state,
        )

        self._dispatchers.append(binary_sensor_dispatcher)
        self._dispatchers.append(connection_dispatcher)

    async def _update_battery_charging(self, data: BatteryState) -> None:
        """Update binary sensor."""
        self._battery = data
        self._attr_is_on = self._battery.is_charging

        self.async_write_ha_state()


class MozartBinarySensorProximity(MozartBinarySensor):
    """Proximity binary sensor for Mozart."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Init the proximity binary sensor."""
        super().__init__(entry)

        self._attr_name = f"{self._name} proximity"
        self._attr_unique_id = f"{self._unique_id}-proximity"
        self._attr_icon = "mdi:account-question"
        self._attr_device_class = "proximity"
        self._attr_is_on = False

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        binary_sensor_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{self._unique_id}_{NOTIFICATION_NOTIFICATION_PROXIMITY}",
            self._update_proximity,
        )

        connection_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{self._unique_id}_{CONNECTION_STATUS}",
            self._update_connection_state,
        )

        self._dispatchers.append(binary_sensor_dispatcher)
        self._dispatchers.append(connection_dispatcher)

    async def _update_proximity(self, data: WebsocketNotificationTag) -> None:
        """Update binary sensor."""
        self._notification = data

        if self._notification.value == "proximityPresenceDetected":
            self._attr_is_on = True
        elif self._notification.value == "proximityPresenceNotDetected":
            self._attr_is_on = False

        self.async_write_ha_state()
