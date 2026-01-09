"""Text entities for the Bang & Olufsen integration."""

from __future__ import annotations

from mozart_api.models import HomeControlUri
from mozart_api.mozart_client import MozartClient

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MODEL, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BeoConfigEntry
from .const import (
    BEO_MODEL_PLATFORM_MAP,
    CONNECTION_STATUS,
    DOMAIN,
    MODEL_SUPPORT_HOME_CONTROL,
    MODEL_SUPPORT_MAP,
    BeoPlatform,
)
from .entity import BeoEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Text entities from config entry."""
    entities: list[BeoText] = []

    match BEO_MODEL_PLATFORM_MAP[config_entry.data[CONF_MODEL]]:
        case BeoPlatform.MOZART.value:
            if (
                config_entry.data[CONF_MODEL]
                in MODEL_SUPPORT_MAP[MODEL_SUPPORT_HOME_CONTROL]
            ):
                entities.append(BeoMozartHomeControlUri(config_entry))
        case BeoPlatform.BEOREMOTE_HALO.value:
            pass

    async_add_entities(new_entities=entities)


class BeoText(TextEntity, BeoEntity):
    """Base Text class."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, config_entry: BeoConfigEntry) -> None:
        """Init the Text entity."""
        super().__init__(config_entry)


# Mozart entities


class BeoMozartHomeControlUri(BeoText):
    """Home Control URI Text."""

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "home_control_uri"

    def __init__(self, config_entry: BeoConfigEntry) -> None:
        """Init the Home Control URI Text."""
        super().__init__(config_entry)
        self._client: MozartClient

        self._attr_unique_id = f"{self._unique_id}_home_control_uri"

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self._unique_id}_{CONNECTION_STATUS}",
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
