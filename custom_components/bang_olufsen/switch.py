"""Switch entities for the Bang & Olufsen integration."""

from __future__ import annotations

from typing import Any

from mozart_api.models import Loudness, SoundSettings

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONNECTION_STATUS, WebsocketNotification
from .entity import BangOlufsenEntity
from .util import BangOlufsenConfigEntry, set_platform_initialized


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BangOlufsenConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Switches from config_entry."""
    entities: list[BangOlufsenEntity] = [BangOlufsenSwitchLoudness(config_entry)]

    async_add_entities(new_entities=entities)

    set_platform_initialized(config_entry.runtime_data)


class BangOlufsenSwitch(BangOlufsenEntity, SwitchEntity):
    """Base Switch class."""

    def __init__(self, config_entry: BangOlufsenConfigEntry) -> None:
        """Init the Switch."""
        super().__init__(config_entry)

        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._attr_entity_category = EntityCategory.CONFIG


class BangOlufsenSwitchLoudness(BangOlufsenSwitch):
    """Loudness Switch."""

    _attr_icon = "mdi:music-note-plus"
    _attr_translation_key = "loudness"

    def __init__(self, config_entry: BangOlufsenConfigEntry) -> None:
        """Init the loudness Switch."""
        super().__init__(config_entry)

        self._attr_unique_id = f"{self._unique_id}-loudness"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Activate the option."""
        await self._client.set_sound_settings_adjustments_loudness(
            loudness=Loudness(value=True),
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Deactivate the option."""
        await self._client.set_sound_settings_adjustments_loudness(
            loudness=Loudness(value=False),
        )

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
                f"{self._unique_id}_{WebsocketNotification.SOUND_SETTINGS}",
                self._update_sound_settings,
            )
        )

    async def _update_sound_settings(self, data: SoundSettings) -> None:
        """Update sound settings."""
        if data.adjustments and data.adjustments.loudness is not None:
            self._attr_is_on = data.adjustments.loudness
            self.async_write_ha_state()
