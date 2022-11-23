"""Button entities for the Bang & Olufsen Mozart integration."""
from __future__ import annotations

import logging

from mozart_api.models import Preset

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_ID, CONF_TYPE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONNECTION_STATUS,
    HASS_PRESETS,
    MOZART_DOMAIN,
    MOZART_EVENT,
    MozartVariables,
    get_device,
)
from .coordinator import MozartCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set Mozart button entities from config entry."""
    entities = []
    configuration = hass.data[MOZART_DOMAIN][config_entry.unique_id]

    # Add preset button entities.
    for button in configuration[HASS_PRESETS]:
        entities.append(button)

    async_add_entities(new_entities=entities, update_before_add=True)


class MozartButton(ButtonEntity, MozartVariables):
    """Button for Mozart actions."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Init the Mozart select."""
        super().__init__(entry)

        self._attr_entity_category = None
        self._attr_available = True
        self._attr_device_class = ButtonDeviceClass.UPDATE
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


class MozartButtonPreset(CoordinatorEntity, MozartButton):
    """Preset button."""

    def __init__(
        self,
        entry: ConfigEntry,
        coordinator: MozartCoordinator,
        preset: Preset,
    ) -> None:
        """Init a preset button."""
        CoordinatorEntity.__init__(self, coordinator)
        MozartButton.__init__(self, entry)

        self._preset_id: int = int(preset.name[6:])
        self._preset: Preset = preset
        self._device: DeviceEntry | None = get_device(self.hass, self._unique_id)
        self._attr_name = f"{self._name} Preset {self._preset_id}"

        self._attr_unique_id = f"{self._unique_id}-preset-{self._preset_id}"
        self._attr_device_class = None

        if self._preset_id in range(10):
            self._attr_icon = f"mdi:numeric-{self._preset_id}-box"
        else:
            self._attr_icon = "mdi:numeric-9-plus-box"

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        connection_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{self.entry.unique_id}_{CONNECTION_STATUS}",
            self._update_connection_state,
        )

        self._dispatchers.append(connection_dispatcher)

        self.async_on_remove(self.coordinator.async_add_listener(self._update_preset))

        self._attr_extra_state_attributes = self.generate_preset_attributes(
            self._preset
        )

    async def async_press(self) -> None:
        """Handle the action."""
        self._mozart_client.activate_preset(id=self._preset_id, async_req=True)

        # Trigger the trigger for the physical button presets.
        if 0 < self._preset_id < 5:
            if not isinstance(self._device, DeviceEntry):
                self._device = get_device(self.hass, self._unique_id)

            assert isinstance(self._device, DeviceEntry)

            self.hass.bus.async_fire(
                MOZART_EVENT,
                event_data={
                    CONF_TYPE: f"{self._preset.name}_shortPress",
                    CONF_DEVICE_ID: self._device.id,
                },
            )

    @callback
    def _update_preset(self) -> None:
        """Update preset attribute."""
        old_preset = self._preset
        self._preset = self.coordinator.data["presets"][str(self._preset_id)]

        if old_preset != self._preset:
            self._attr_extra_state_attributes = self.generate_preset_attributes(
                self._preset
            )

            self.async_write_ha_state()
