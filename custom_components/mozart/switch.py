"""Switch entities for the Bang & Olufsen Mozart integration."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from mozart_api.models import Loudness, SoundSettings

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONNECTION_STATUS,
    HASS_SWITCHES,
    MOZART_DOMAIN,
    SOUND_SETTINGS_NOTIFICATION,
    MozartVariables,
)

SCAN_INTERVAL = timedelta(seconds=120)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Mozart switch entities from config entry."""
    entities = []

    # Add switch entities.
    for switch in hass.data[MOZART_DOMAIN][config_entry.unique_id][HASS_SWITCHES]:
        entities.append(switch)

    async_add_entities(new_entities=entities, update_before_add=True)


class MozartSwitch(MozartVariables, SwitchEntity):
    """Number for Mozart settings."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Init the Mozart number."""
        super().__init__(entry)

        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._attr_available = True
        self._attr_should_poll = False
        self._attr_device_info = DeviceInfo(
            identifiers={(MOZART_DOMAIN, self._unique_id)}
        )
        self._attr_is_on = False

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

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the option."""
        if self._attr_is_on:
            await self.async_turn_off()
        else:
            await self.async_turn_on()


class MozartSwitchLoudness(MozartSwitch):
    """Loudness switch for Mozart settings."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Init the loudness switch."""
        super().__init__(entry)

        self._attr_name = f"{self._name} Loudness"
        self._attr_unique_id = f"{self._unique_id}-loudness"
        self._attr_icon = "mdi:music-note-plus"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Activate the option."""
        self._mozart_client.set_sound_settings_adjustments_loudness(
            loudness=Loudness(value=True),
            async_req=True,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Deactivate the option."""
        self._mozart_client.set_sound_settings_adjustments_loudness(
            loudness=Loudness(value=False),
            async_req=True,
        )

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        switch_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{self._unique_id}_{SOUND_SETTINGS_NOTIFICATION}",
            self._update_sound_settings,
        )

        connection_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{self._unique_id}_{CONNECTION_STATUS}",
            self._update_connection_state,
        )

        self._dispatchers.append(switch_dispatcher)
        self._dispatchers.append(connection_dispatcher)

    async def _update_sound_settings(self, data: SoundSettings) -> None:
        """Update sound settings."""
        sound_settings = data
        self._attr_is_on = sound_settings.adjustments.loudness

        self.async_write_ha_state()
