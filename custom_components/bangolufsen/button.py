"""Button entities for the Bang & Olufsen integration."""
from __future__ import annotations

from mozart_api.models import Preset

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONNECTION_STATUS,
    DOMAIN,
    HASS_FAVOURITES,
    BangOlufsenVariables,
    get_device,
)
from .coordinator import BangOlufsenCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Button entities from config entry."""
    entities = []
    configuration = hass.data[DOMAIN][config_entry.unique_id]

    # Add favourite Button entities.
    for button in configuration[HASS_FAVOURITES]:
        entities.append(button)

    async_add_entities(new_entities=entities, update_before_add=True)


class BangOlufsenButton(ButtonEntity, BangOlufsenVariables):
    """Base Button class."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Init the Button."""
        super().__init__(entry)

        self._attr_entity_category = None
        self._attr_available = True
        self._attr_device_class = ButtonDeviceClass.UPDATE
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, self._unique_id)})

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        self._dispatchers = [
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{CONNECTION_STATUS}",
                self._update_connection_state,
            )
        ]

    async def async_will_remove_from_hass(self) -> None:
        """Turn off the dispatchers."""
        for dispatcher in self._dispatchers:
            dispatcher()

    async def _update_connection_state(self, connection_state: bool) -> None:
        """Update entity connection state."""
        self._attr_available = connection_state

        self.async_write_ha_state()


class BangOlufsenButtonFavourite(CoordinatorEntity, BangOlufsenButton):
    """Favourite Button."""

    def __init__(
        self,
        entry: ConfigEntry,
        coordinator: BangOlufsenCoordinator,
        favourite: Preset,
    ) -> None:
        """Init a favourite Button."""
        CoordinatorEntity.__init__(self, coordinator)
        BangOlufsenButton.__init__(self, entry)

        self._favourite_id: int = int(favourite.name[6:])
        self._favourite: Preset = favourite
        self._device: DeviceEntry | None = get_device(self.hass, self._unique_id)
        self._attr_name = f"{self._name} Favourite {self._favourite_id}"

        self._attr_unique_id = f"{self._unique_id}-favourite-{self._favourite_id}"
        self._attr_device_class = None

        if self._favourite_id in range(10):
            self._attr_icon = f"mdi:numeric-{self._favourite_id}-box"
        else:
            self._attr_icon = "mdi:numeric-9-plus-box"

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        self._dispatchers = [
            async_dispatcher_connect(
                self.hass,
                f"{self.entry.unique_id}_{CONNECTION_STATUS}",
                self._update_connection_state,
            )
        ]

        self.async_on_remove(
            self.coordinator.async_add_listener(self._update_favourite)
        )

        self._attr_extra_state_attributes = self.generate_favourite_attributes(
            self._favourite
        )

    async def async_press(self) -> None:
        """Handle the action."""
        self._client.activate_preset(id=self._favourite_id, async_req=True)

    @callback
    def _update_favourite(self) -> None:
        """Update favourite attribute."""
        old_favourite = self._favourite
        self._favourite = self.coordinator.data["favourites"][str(self._favourite_id)]

        if old_favourite != self._favourite:
            self._attr_extra_state_attributes = self.generate_favourite_attributes(
                self._favourite
            )

            self.async_write_ha_state()
