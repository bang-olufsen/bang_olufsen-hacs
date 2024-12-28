"""Sensor entities for the Bang & Olufsen integration."""

from __future__ import annotations

import contextlib
from datetime import timedelta
from typing import cast

from aiohttp import ClientConnectorError
from inflection import titleize, underscore
from mozart_api.exceptions import ApiException
from mozart_api.models import BatteryState, PairedRemote, PlaybackContentMetadata

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HaloConfigEntry, MozartConfigEntry, set_platform_initialized
from .const import CONNECTION_STATUS, DOMAIN, WebsocketNotification
from .entity import HaloEntity, MozartEntity
from .halo import PowerEvent
from .util import get_remotes, is_halo

SCAN_INTERVAL = timedelta(minutes=15)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sensor entities from config entry."""
    entities: list[MozartSensor | HaloSensor] = []

    if is_halo(config_entry):
        entities.extend(await _get_halo_entities(config_entry))
    else:
        entities.extend(await _get_mozart_entities(config_entry))

    async_add_entities(new_entities=entities)

    set_platform_initialized(config_entry.runtime_data)


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
    entities: list[MozartSensor] = [
        MozartSensorInputSignal(config_entry),
        MozartSensorMediaId(config_entry),
    ]

    # Check if device has a battery
    battery_state = await config_entry.runtime_data.client.get_battery_state()

    if battery_state.battery_level and battery_state.battery_level > 0:
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
        self._attr_unique_id = f"{self._unique_id}-battery-level"

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
        self._attr_unique_id = f"{remote.serial_number}_remote_battery_level"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, remote.serial_number)}
        )
        self._attr_native_value = remote.battery_level

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{CONNECTION_STATUS}",
                self._async_update_connection_state,
            )
        )

    async def async_update(self) -> None:
        """Poll battery status."""
        with contextlib.suppress(ApiException, ClientConnectorError, TimeoutError):
            bluetooth_remote_list = await self._client.get_bluetooth_remotes(
                _request_timeout=5
            )

            if bool(len(cast(list[PairedRemote], bluetooth_remote_list.items))):
                remote: PairedRemote = cast(
                    list[PairedRemote], bluetooth_remote_list.items
                )[0]
                self._attr_native_value = remote.battery_level


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
        self._attr_unique_id = f"{self._unique_id}-battery-charging-time"

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
                self._update_battery,
            )
        )

    async def _update_battery(self, data: BatteryState) -> None:
        """Update sensor value."""

        self._attr_available = True

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

        self._attr_unique_id = f"{self._unique_id}-battery-playing-time"

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
                self._update_battery,
            )
        )

    async def _update_battery(self, data: BatteryState) -> None:
        """Update sensor value."""
        self._attr_available = True

        playing_time = cast(int, data.remaining_playing_time_minutes)

        # The playing time is 65535 if the device is charging
        if playing_time == 65535:
            self._attr_native_value = 0

        else:
            self._attr_native_value = playing_time

        self.async_write_ha_state()


class MozartSensorMediaId(MozartSensor):
    """Media id Sensor."""

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "media_id"

    def __init__(self, config_entry: MozartConfigEntry) -> None:
        """Init the media id Sensor."""
        super().__init__(config_entry)

        self._attr_device_class = None
        # self._attr_state_class = SensorStateClass.
        self._attr_native_value = None
        self._attr_unique_id = f"{self._unique_id}-media-id"

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
                f"{self._unique_id}_{WebsocketNotification.PLAYBACK_METADATA}",
                self._update_playback_metadata,
            )
        )

    async def _update_playback_metadata(self, data: PlaybackContentMetadata) -> None:
        """Update Sensor value."""
        self._attr_native_value = data.source_internal_id
        self.async_write_ha_state()


class MozartSensorInputSignal(MozartSensor):
    """Input signal Sensor."""

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "input_signal"

    def __init__(self, config_entry: MozartConfigEntry) -> None:
        """Init the input signal Sensor."""
        super().__init__(config_entry)

        self._attr_device_class = None
        # self._attr_state_class = None
        self._attr_unique_id = f"{self._unique_id}-input-signal"

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
                f"{self._unique_id}_{WebsocketNotification.PLAYBACK_METADATA}",
                self._update_playback_metadata,
            )
        )

    async def _update_playback_metadata(self, data: PlaybackContentMetadata) -> None:
        """Update Sensor value."""
        if data.encoding:
            # Ensure that abbreviated formats are capitialized and non-abbreviated formats are made "human readable"
            encoding = titleize(underscore(data.encoding))
            if data.encoding.capitalize() == encoding:
                encoding = data.encoding.upper()

            input_channel_processing = None
            if data.input_channel_processing:
                input_channel_processing = titleize(
                    underscore(data.input_channel_processing)
                )

            self._attr_native_value = f"{encoding}{f' - {input_channel_processing}' if input_channel_processing else ''}{f' - {data.input_channels}' if data.input_channels else ''}"
        else:
            self._attr_native_value = None

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
        self._attr_unique_id = f"{self._unique_id}-battery-level"

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
                self._update_battery,
            )
        )

    async def _update_battery(self, data: PowerEvent) -> None:
        """Update sensor value."""
        self._attr_native_value = data.capacity
        self.async_write_ha_state()
