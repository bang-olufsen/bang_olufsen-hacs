"""Number entities for the Bang & Olufsen integration."""

from __future__ import annotations

from mozart_api.models import Bass, SoundSettings, Treble
from mozart_api.mozart_client import MozartClient

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BangOlufsenData
from .const import BASS_TREBLE_RANGE, CONNECTION_STATUS, DOMAIN, WebsocketNotification
from .entity import BangOlufsenEntity
from .util import set_platform_initialized


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Number entities from config entry."""
    data: BangOlufsenData = hass.data[DOMAIN][config_entry.entry_id]
    entities: list[BangOlufsenEntity] = [
        BangOlufsenNumberBass(config_entry, data.client),
        BangOlufsenNumberTreble(config_entry, data.client),
    ]

    async_add_entities(new_entities=entities)

    set_platform_initialized(data)


class BangOlufsenNumber(BangOlufsenEntity, NumberEntity):
    """Base Number class."""

    _attr_mode = NumberMode.AUTO

    def __init__(self, entry: ConfigEntry, client: MozartClient) -> None:
        """Init the Number."""
        super().__init__(entry, client)

        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_native_value = 0.0


class BangOlufsenNumberTreble(BangOlufsenNumber):
    """Treble Number."""

    _attr_icon = "mdi:equalizer"
    _attr_native_max_value = float(BASS_TREBLE_RANGE.stop)
    _attr_native_min_value = float(BASS_TREBLE_RANGE.start)
    _attr_translation_key = "treble"

    def __init__(self, entry: ConfigEntry, client: MozartClient) -> None:
        """Init the treble Number."""
        super().__init__(entry, client)

        self._attr_mode = NumberMode.SLIDER
        self._attr_unique_id = f"{self._unique_id}-treble"

    async def async_set_native_value(self, value: float) -> None:
        """Set the treble value."""
        await self._client.set_sound_settings_adjustments_treble(
            treble=Treble(value=int(value))
        )

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
                f"{self._unique_id}_{WebsocketNotification.SOUND_SETTINGS}",
                self._update_sound_settings,
            )
        )

        self.set_entity_initialized()

    async def _update_sound_settings(self, data: SoundSettings) -> None:
        """Update sound settings."""
        if data.adjustments and data.adjustments.treble:
            self._attr_native_value = data.adjustments.treble
            self.async_write_ha_state()


class BangOlufsenNumberBass(BangOlufsenNumber):
    """Bass Number."""

    _attr_icon = "mdi:equalizer"
    _attr_native_max_value = float(BASS_TREBLE_RANGE.stop)
    _attr_native_min_value = float(BASS_TREBLE_RANGE.start)
    _attr_translation_key = "bass"

    def __init__(self, entry: ConfigEntry, client: MozartClient) -> None:
        """Init the bass Number."""
        super().__init__(entry, client)

        self._attr_mode = NumberMode.SLIDER
        self._attr_unique_id = f"{self._unique_id}-bass"

    async def async_set_native_value(self, value: float) -> None:
        """Set the bass value."""
        await self._client.set_sound_settings_adjustments_bass(
            bass=Bass(value=int(value))
        )

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
                f"{self._unique_id}_{WebsocketNotification.SOUND_SETTINGS}",
                self._update_sound_settings,
            )
        )

        self.set_entity_initialized()

    async def _update_sound_settings(self, data: SoundSettings) -> None:
        """Update sound settings."""
        if data.adjustments and data.adjustments.bass:
            self._attr_native_value = data.adjustments.bass
            self.async_write_ha_state()
