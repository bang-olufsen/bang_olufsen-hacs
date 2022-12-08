"""Button entities for the Bang & Olufsen integration."""
from __future__ import annotations

import logging

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONNECTION_STATUS, DOMAIN, HASS_TEXT, MEDIA_ID, BangOlufsenVariables

# from mozart_api.models import HomeControlUri


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Text entities from config entry."""
    entities = []
    configuration = hass.data[DOMAIN][config_entry.unique_id]

    # Add favourite Button entities.
    for text in configuration[HASS_TEXT]:
        entities.append(text)

    async_add_entities(new_entities=entities, update_before_add=True)


class BangOlufsenText(TextEntity, BangOlufsenVariables):
    """Base Text class."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Init the Text."""
        super().__init__(entry)

        self._attr_entity_category = None
        self._attr_available = True
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


class BangOlufsenTextMediaId(BangOlufsenText):
    """Media id Text."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Init the media id Text."""
        super().__init__(entry)

        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_name = f"{self._name} Media Id"
        self._attr_unique_id = f"{self._unique_id}-media-id"
        self._attr_device_class = None
        self._attr_icon = "mdi:information"
        self._attr_entity_registry_enabled_default = False

        self._attr_native_value = None

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        self._dispatchers = [
            async_dispatcher_connect(
                self.hass,
                f"{self.entry.unique_id}_{CONNECTION_STATUS}",
                self._update_connection_state,
            ),
            async_dispatcher_connect(
                self.hass,
                f"{self.entry.unique_id}_{MEDIA_ID}",
                self._update_media_id,
            ),
        ]

    async def _update_media_id(self, data: str | None) -> None:
        """Update text value."""
        self._attr_native_value = data

        self.async_write_ha_state()
