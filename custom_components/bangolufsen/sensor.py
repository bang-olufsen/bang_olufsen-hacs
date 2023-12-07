"""Sensor entities for the Bang & Olufsen integration."""
from __future__ import annotations

from typing import cast

from inflection import titleize, underscore
from mozart_api.models import BatteryState, PlaybackContentMetadata
from mozart_api.mozart_client import MozartClient

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BangOlufsenData
from .const import CONNECTION_STATUS, DOMAIN, WEBSOCKET_NOTIFICATION
from .entity import BangOlufsenEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sensor entities from config entry."""
    data: BangOlufsenData = hass.data[DOMAIN][config_entry.entry_id]
    entities: list[BangOlufsenSensor] = [
        BangOlufsenSensorInputSignal(config_entry, data.client),
        BangOlufsenSensorMediaId(config_entry, data.client),
    ]

    # Check if device has a battery
    battery_state = await data.client.get_battery_state()

    if battery_state.battery_level and battery_state.battery_level > 0:
        entities.extend(
            [
                BangOlufsenSensorBatteryChargingTime(config_entry, data.client),
                BangOlufsenSensorBatteryLevel(config_entry, data.client),
                BangOlufsenSensorBatteryPlayingTime(config_entry, data.client),
            ]
        )

    async_add_entities(new_entities=entities)


class BangOlufsenSensor(BangOlufsenEntity, SensorEntity):
    """Base Sensor class."""

    def __init__(self, entry: ConfigEntry, client: MozartClient) -> None:
        """Init the Sensor."""
        super().__init__(entry, client)

        self._attr_state_class = SensorStateClass.MEASUREMENT


class BangOlufsenSensorBatteryLevel(BangOlufsenSensor):
    """Battery level Sensor."""

    _attr_icon = "mdi:battery"
    _attr_native_unit_of_measurement = "%"
    _attr_translation_key = "battery_level"

    def __init__(self, entry: ConfigEntry, client: MozartClient) -> None:
        """Init the battery level Sensor."""
        super().__init__(entry, client)

        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_unique_id = f"{self._unique_id}-battery-level"

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{CONNECTION_STATUS}",
                self._update_connection_state,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{WEBSOCKET_NOTIFICATION.BATTERY}",
                self._update_battery,
            )
        )

    async def _update_battery(self, data: BatteryState) -> None:
        """Update sensor value."""
        self._attr_native_value = data.battery_level
        self.async_write_ha_state()


class BangOlufsenSensorBatteryChargingTime(BangOlufsenSensor):
    """Battery charging time Sensor."""

    _attr_entity_registry_enabled_default = False
    _attr_icon = "mdi:battery-arrow-up"
    _attr_native_unit_of_measurement = "min"
    _attr_translation_key = "battery_charging_time"

    def __init__(self, entry: ConfigEntry, client: MozartClient) -> None:
        """Init the battery charging time Sensor."""
        super().__init__(entry, client)

        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_unique_id = f"{self._unique_id}-battery-charging-time"

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{CONNECTION_STATUS}",
                self._update_connection_state,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{WEBSOCKET_NOTIFICATION.BATTERY}",
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


class BangOlufsenSensorBatteryPlayingTime(BangOlufsenSensor):
    """Battery playing time Sensor."""

    _attr_entity_registry_enabled_default = False
    _attr_icon = "mdi:battery-arrow-down"
    _attr_native_unit_of_measurement = "min"
    _attr_translation_key = "battery_playing_time"

    def __init__(self, entry: ConfigEntry, client: MozartClient) -> None:
        """Init the battery playing time Sensor."""
        super().__init__(entry, client)

        self._attr_unique_id = f"{self._unique_id}-battery-playing-time"

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{CONNECTION_STATUS}",
                self._update_connection_state,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{WEBSOCKET_NOTIFICATION.BATTERY}",
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


class BangOlufsenSensorMediaId(BangOlufsenSensor):
    """Media id Sensor."""

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "media_id"
    _attr_icon = "mdi:information"

    def __init__(self, entry: ConfigEntry, client: MozartClient) -> None:
        """Init the media id Sensor."""
        super().__init__(entry, client)

        self._attr_device_class = None
        self._attr_state_class = None
        self._attr_native_value = None
        self._attr_unique_id = f"{self._unique_id}-media-id"

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{CONNECTION_STATUS}",
                self._update_connection_state,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self.entry.unique_id}_{WEBSOCKET_NOTIFICATION.PLAYBACK_METADATA}",
                self._update_playback_metadata,
            )
        )

    async def _update_playback_metadata(self, data: PlaybackContentMetadata) -> None:
        """Update Sensor value."""
        self._attr_native_value = data.source_internal_id
        self.async_write_ha_state()


class BangOlufsenSensorInputSignal(BangOlufsenSensor):
    """Input signal Sensor."""

    _attr_entity_registry_enabled_default = False
    _attr_icon = "mdi:audio-input-stereo-minijack"
    _attr_translation_key = "input_signal"

    def __init__(self, entry: ConfigEntry, client: MozartClient) -> None:
        """Init the input signal Sensor."""
        super().__init__(entry, client)

        self._attr_device_class = None
        self._attr_state_class = None
        self._attr_unique_id = f"{self._unique_id}-input-signal"

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{CONNECTION_STATUS}",
                self._update_connection_state,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{WEBSOCKET_NOTIFICATION.PLAYBACK_METADATA}",
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
