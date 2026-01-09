"""Sensor entities for the Bang & Olufsen integration."""

from __future__ import annotations

import contextlib
from datetime import timedelta
from typing import cast

from aiohttp import ClientConnectorError
from mozart_api.exceptions import ApiException
from mozart_api.models import BatteryState, PairedRemote

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MODEL, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BeoConfigEntry
from .beoremote_halo.models import PowerEvent
from .const import (
    BEO_MODEL_PLATFORM_MAP,
    CONNECTION_STATUS,
    DOMAIN,
    BeoPlatform,
    WebsocketNotification,
)
from .entity import BeoEntity
from .util import get_remotes, supports_battery

SCAN_INTERVAL = timedelta(minutes=15)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Sensor entities from config entry."""
    entities: list[BeoSensor] = []

    match BEO_MODEL_PLATFORM_MAP[config_entry.data[CONF_MODEL]]:
        case BeoPlatform.MOZART.value:
            if await supports_battery(config_entry.runtime_data.client):
                entities.extend(
                    [
                        BeoMozartBatteryChargingTime(config_entry),
                        BeoMozartBatteryLevel(config_entry),
                        BeoMozartBatteryPlayingTime(config_entry),
                    ]
                )

            # Check for connected Beoremote One
            if remotes := await get_remotes(config_entry.runtime_data.client):
                entities.extend(
                    [
                        BeoMozartRemoteBatteryLevel(config_entry, remote)
                        for remote in remotes
                    ]
                )
        case BeoPlatform.BEOREMOTE_HALO.value:
            entities.append(BeoHaloBatteryLevel(config_entry))

    async_add_entities(new_entities=entities, update_before_add=True)


class BeoSensor(SensorEntity, BeoEntity):
    """Base Bang & Olufsen Sensor."""

    def __init__(self, config_entry: BeoConfigEntry) -> None:
        """Initialize Sensor."""
        super().__init__(config_entry)


class BeoMozartBatteryLevel(BeoSensor):
    """Battery level Sensor."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, config_entry: BeoConfigEntry) -> None:
        """Init the battery level Sensor."""
        super().__init__(config_entry)

        self._attr_unique_id = f"{self._unique_id}_battery_level"

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
                self._update_battery,
            )
        )

    async def _update_battery(self, data: BatteryState) -> None:
        """Update sensor value."""
        self._attr_native_value = data.battery_level
        self.async_write_ha_state()


class BeoMozartRemoteBatteryLevel(BeoSensor):
    """Battery level Sensor for the Beoremote One."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_should_poll = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, config_entry: BeoConfigEntry, remote: PairedRemote) -> None:
        """Init the battery level Sensor."""
        super().__init__(config_entry)
        # Serial number is not None, as the remote object is provided by get_remotes
        assert remote.serial_number

        self._attr_unique_id = (
            f"{remote.serial_number}_{self._unique_id}_remote_battery_level"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{remote.serial_number}_{self._unique_id}")}
        )
        self._attr_native_value = remote.battery_level
        self._remote = remote

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self._unique_id}_{CONNECTION_STATUS}",
                self._async_update_connection_state,
            )
        )

    async def async_update(self) -> None:
        """Poll battery status."""
        with contextlib.suppress(ApiException, ClientConnectorError, TimeoutError):
            for remote in await get_remotes(self._client):
                if remote.serial_number == self._remote.serial_number:
                    self._attr_native_value = remote.battery_level
                    break


class BeoMozartBatteryChargingTime(BeoSensor):
    """Battery charging time Sensor."""

    _attr_entity_registry_enabled_default = False
    _attr_native_unit_of_measurement = "min"
    _attr_translation_key = "battery_charging_time"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, config_entry: BeoConfigEntry) -> None:
        """Init the battery charging time Sensor."""
        super().__init__(config_entry)

        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_unique_id = f"{self._unique_id}_battery_charging_time"

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
                self._update_battery,
            )
        )

    async def _update_battery(self, data: BatteryState) -> None:
        """Update sensor value."""

        charging_time = data.remaining_charging_time_minutes

        # The charging time is 65535 if the device is not charging.
        if charging_time == 65535:
            self._attr_native_value = 0
        else:
            self._attr_native_value = charging_time

        self.async_write_ha_state()


class BeoMozartBatteryPlayingTime(BeoSensor):
    """Battery playing time Sensor."""

    _attr_entity_registry_enabled_default = False
    _attr_native_unit_of_measurement = "min"
    _attr_translation_key = "battery_playing_time"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, config_entry: BeoConfigEntry) -> None:
        """Init the battery playing time Sensor."""
        super().__init__(config_entry)

        self._attr_unique_id = f"{self._unique_id}_battery_playing_time"

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
                self._update_battery,
            )
        )

    async def _update_battery(self, data: BatteryState) -> None:
        """Update sensor value."""
        playing_time = cast(int, data.remaining_playing_time_minutes)

        # The playing time is 65535 if the device is charging
        if playing_time == 65535:
            self._attr_native_value = 0
        else:
            self._attr_native_value = playing_time

        self.async_write_ha_state()


# Halo entities


class BeoHaloBatteryLevel(BeoSensor):
    """Halo battery level Sensor."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, config_entry: BeoConfigEntry) -> None:
        """Init the battery level Sensor."""
        super().__init__(config_entry)

        self._attr_unique_id = f"{self._unique_id}_battery_level"

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
                self._update_battery,
            )
        )

    async def _update_battery(self, data: PowerEvent) -> None:
        """Update sensor value."""
        self._attr_native_value = data.capacity
        self.async_write_ha_state()
