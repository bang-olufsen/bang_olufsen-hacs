"""Binary Sensor entities for the Bang & Olufsen integration."""

from __future__ import annotations

from mozart_api.models import BatteryState

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import CONF_MODEL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BeoConfigEntry
from .beoremote_halo.models import PowerEvent, PowerEventState
from .const import (
    BEO_MODEL_PLATFORM_MAP,
    CONNECTION_STATUS,
    DOMAIN,
    WebsocketNotification,
)
from .entity import BeoEntity, BeoPlatform
from .util import supports_battery


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BeoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Binary Sensor entities from config entry."""
    entities: list[BeoBinarySensor] = []

    match BEO_MODEL_PLATFORM_MAP[config_entry.data[CONF_MODEL]]:
        case BeoPlatform.MOZART.value:
            if await supports_battery(config_entry.runtime_data.client):
                entities.append(BeoMozartBatteryCharging(config_entry))
        case BeoPlatform.BEOREMOTE_HALO.value:
            entities.append(BeoHaloBatteryCharging(config_entry))

    async_add_entities(new_entities=entities)


class BeoBinarySensor(BinarySensorEntity, BeoEntity):
    """Base Binary Sensor class."""

    _attr_is_on = False

    def __init__(self, config_entry: BeoConfigEntry) -> None:
        """Init the Binary Sensor."""
        super().__init__(config_entry)


class BeoMozartBatteryCharging(BeoBinarySensor):
    """Battery charging Binary Sensor."""

    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING

    def __init__(self, config_entry: BeoConfigEntry) -> None:
        """Init the battery charging Binary Sensor."""
        super().__init__(config_entry)

        self._attr_unique_id = f"{self._unique_id}_battery_charging"

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self._unique_id}_{CONNECTION_STATUS}",
                self._async_update_connection_state,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self._unique_id}_{WebsocketNotification.BATTERY}",
                self._update_battery_charging,
            )
        )

    async def _update_battery_charging(self, data: BatteryState) -> None:
        """Update battery charging."""
        self._attr_is_on = bool(data.is_charging)
        self.async_write_ha_state()


class BeoHaloBatteryCharging(BeoBinarySensor):
    """Battery charging Binary Sensor."""

    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING

    def __init__(self, config_entry: BeoConfigEntry) -> None:
        """Init the battery charging Binary Sensor."""
        super().__init__(config_entry)

        self._attr_unique_id = f"{self._unique_id}_battery_charging"

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self._unique_id}_{CONNECTION_STATUS}",
                self._async_update_connection_state,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self._unique_id}_{WebsocketNotification.HALO_POWER}",
                self._update_battery_charging,
            )
        )

    async def _update_battery_charging(self, data: PowerEvent) -> None:
        """Update battery charging."""
        self._attr_is_on = data.state == PowerEventState.CHARGING
        self.async_write_ha_state()
