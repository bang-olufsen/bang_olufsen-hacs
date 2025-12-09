"""Text entities for the Bang & Olufsen integration."""

from __future__ import annotations

from mozart_api.models import HomeControlUri

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MODEL, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MozartConfigEntry
from .const import (
    CONNECTION_STATUS,
    DOMAIN,
    MODEL_SUPPORT_HOME_CONTROL,
    MODEL_SUPPORT_MAP,
)
from .entity import MozartEntity
from .util import is_halo, is_mozart

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Text entities from config entry."""
    entities: list[BeoText] = []

    if is_halo(config_entry):
        pass
    elif is_mozart(config_entry):
        entities.extend(await _get_mozart_entities(config_entry))

    async_add_entities(new_entities=entities)


class BeoText(TextEntity):
    """Base Text class."""

    _attr_entity_category = EntityCategory.CONFIG


# Mozart entities
class MozartText(BeoText, MozartEntity):
    """Base Mozart Text class."""

    def __init__(self, config_entry: MozartConfigEntry) -> None:
        """Init the Text entity."""
        super().__init__(config_entry)


async def _get_mozart_entities(config_entry: MozartConfigEntry) -> list[MozartText]:
    """Get Mozart Sensor entities from config entry."""
    entities: list[MozartText] = []

    # Add the Home Control URI entity if the device supports it
    if config_entry.data[CONF_MODEL] in MODEL_SUPPORT_MAP[MODEL_SUPPORT_HOME_CONTROL]:
        entities.append(MozartTextHomeControlUri(config_entry))

    return entities


class MozartTextHomeControlUri(MozartText):
    """Home Control URI Text."""

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "home_control_uri"

    def __init__(self, config_entry: MozartConfigEntry) -> None:
        """Init the Home Control URI Text."""
        super().__init__(config_entry)

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
