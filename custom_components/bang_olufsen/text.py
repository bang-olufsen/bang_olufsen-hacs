"""Text entities for the Bang & Olufsen integration."""

from __future__ import annotations

from mozart_api.models import HomeControlUri

from homeassistant.components.text import TextEntity
from homeassistant.const import CONF_MODEL, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BangOlufsenConfigEntry, set_platform_initialized
from .const import CONNECTION_STATUS, MODEL_SUPPORT_HOME_CONTROL, MODEL_SUPPORT_MAP
from .entity import BangOlufsenEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BangOlufsenConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Text entities from config entry."""
    entities: list[BangOlufsenEntity] = []

    # Add the Home Control URI entity if the device supports it
    if config_entry.data[CONF_MODEL] in MODEL_SUPPORT_MAP[MODEL_SUPPORT_HOME_CONTROL]:
        entities.append(BangOlufsenTextHomeControlUri(config_entry))

    async_add_entities(new_entities=entities)

    set_platform_initialized(config_entry.runtime_data)


class BangOlufsenText(TextEntity, BangOlufsenEntity):
    """Base Text class."""

    def __init__(self, config_entry: BangOlufsenConfigEntry) -> None:
        """Init the Text."""
        super().__init__(config_entry)

        self._attr_entity_category = EntityCategory.CONFIG


class BangOlufsenTextHomeControlUri(BangOlufsenText):
    """Home Control URI Text."""

    _attr_entity_registry_enabled_default = False
    _attr_icon = "mdi:link-variant"
    _attr_translation_key = "home_control_uri"

    def __init__(self, config_entry: BangOlufsenConfigEntry) -> None:
        """Init the Home Control URI Text."""
        super().__init__(config_entry)

        self._attr_unique_id = f"{self._unique_id}-home-control-uri"

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{CONNECTION_STATUS}",
                self._async_update_connection_state,
            )
        )

        home_control = await self._client.get_remote_home_control_uri()
        self._attr_native_value = home_control.uri

    async def async_set_value(self, value: str) -> None:
        """Set the Home Control URI name."""
        self._attr_native_value = value

        await self._client.set_remote_home_control_uri(
            home_control_uri=HomeControlUri(uri=value)
        )
