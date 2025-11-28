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
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import HaloConfigEntry, MozartConfigEntry
from .beoremote_halo.models import PowerEvent
from .const import CONNECTION_STATUS, DOMAIN, WebsocketNotification
from .entity import HaloEntity, MozartEntity
from .util import get_remotes, is_halo, supports_battery

SCAN_INTERVAL = timedelta(minutes=15)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Sensor entities from config entry."""
    entities: list[MozartSensor | HaloSensor] = []

    if is_halo(config_entry):
        entities.extend(await _get_halo_entities(config_entry))
    else:
        entities.extend(await _get_mozart_entities(config_entry))

    async_add_entities(new_entities=entities, update_before_add=True)


# Mozart entities
class MozartSensor(MozartEntity, SensorEntity):
    """Base Mozart Sensor class."""

    def __init__(self, config_entry: MozartConfigEntry) -> None:
        """Init the Sensor."""
        super().__init__(config_entry)


async def _get_mozart_entities(
    config_entry: MozartConfigEntry,
) -> list[MozartSensor]:
    """Get Mozart Sensor entities from config entry."""
    entities: list[MozartSensor] = []

    if await supports_battery(config_entry.runtime_data.client):
        entities.extend(
            [
                MozartSensorBatteryChargingTime(config_entry),
                MozartSensorBatteryLevel(config_entry),
                MozartSensorBatteryPlayingTime(config_entry),
            ]
        )

    # Check for connected Beoremote One
    if remotes := await get_remotes(config_entry.runtime_data.client):
        entities.extend(
            [MozartSensorRemoteBatteryLevel(config_entry, remote) for remote in remotes]
        )

    return entities


class MozartSensorBatteryLevel(MozartSensor):
    """Battery level Sensor."""

    _attr_native_unit_of_measurement = "%"
    _attr_translation_key = "battery_level"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, config_entry: MozartConfigEntry) -> None:
        """Init the battery level Sensor."""
        super().__init__(config_entry)

        self._attr_device_class = SensorDeviceClass.BATTERY
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


class MozartSensorRemoteBatteryLevel(MozartSensor):
    """Battery level Sensor for the Beoremote One."""

    _attr_native_unit_of_measurement = "%"
    _attr_translation_key = "remote_battery_level"
    _attr_should_poll = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, config_entry: MozartConfigEntry, remote: PairedRemote) -> None:
        """Init the battery level Sensor."""
        super().__init__(config_entry)
        assert remote.serial_number

        self._attr_device_class = SensorDeviceClass.BATTERY
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


class MozartSensorBatteryChargingTime(MozartSensor):
    """Battery charging time Sensor."""

    _attr_entity_registry_enabled_default = False
    _attr_native_unit_of_measurement = "min"
    _attr_translation_key = "battery_charging_time"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, config_entry: MozartConfigEntry) -> None:
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


class MozartSensorBatteryPlayingTime(MozartSensor):
    """Battery playing time Sensor."""

    _attr_entity_registry_enabled_default = False
    _attr_native_unit_of_measurement = "min"
    _attr_translation_key = "battery_playing_time"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, config_entry: MozartConfigEntry) -> None:
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


async def _get_halo_entities(
    config_entry: HaloConfigEntry,
) -> list[HaloSensor]:
    """Get Halo Sensor entities from config entry."""
    entities: list[HaloSensor] = [HaloSensorBatteryLevel(config_entry)]
    return entities


class HaloSensor(HaloEntity, SensorEntity):
    """Base Halo Sensor class."""

    def __init__(self, config_entry: HaloConfigEntry) -> None:
        """Init the Sensor."""
        super().__init__(config_entry)


class HaloSensorBatteryLevel(HaloSensor):
    """Halo battery level Sensor."""

    _attr_native_unit_of_measurement = "%"
    _attr_translation_key = "halo_battery_level"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, config_entry: HaloConfigEntry) -> None:
        """Init the battery level Sensor."""
        super().__init__(config_entry)

        self._attr_device_class = SensorDeviceClass.BATTERY
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
