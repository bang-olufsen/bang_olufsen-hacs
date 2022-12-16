"""Number entities for the Bang & Olufsen integration."""
from __future__ import annotations

from mozart_api.models import Bass, SoundSettings, Treble

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONNECTION_STATUS,
    DOMAIN,
    HASS_NUMBERS,
    BangOlufsenVariables,
    WebSocketNotification,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Number entities from config entry."""
    entities = []

    # Add number entities.
    for number in hass.data[DOMAIN][config_entry.unique_id][HASS_NUMBERS]:
        entities.append(number)

    async_add_entities(new_entities=entities, update_before_add=True)


class BangOlufsenNumber(BangOlufsenVariables, NumberEntity):
    """Base Number class."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Init the Number."""
        super().__init__(entry)

        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_should_poll = False
        self._attr_mode = NumberMode.AUTO
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, self._unique_id)})
        self._attr_native_value = 0.0

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


class BangOlufsenNumberTreble(BangOlufsenNumber):
    """Treble Number."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Init the treble Number."""
        super().__init__(entry)

        number_range: range = range(-6, 6, 1)
        self._attr_native_min_value = float(number_range.start)
        self._attr_native_max_value = float(number_range.stop)
        self._attr_name = f"{self._name} Treble"
        self._attr_unique_id = f"{self._unique_id}-treble"
        self._attr_icon = "mdi:equalizer"
        self._attr_mode = NumberMode.SLIDER

    async def async_set_native_value(self, value: float) -> None:
        """Set the treble value."""
        self._client.set_sound_settings_adjustments_treble(
            treble=Treble(value=value), async_req=True
        )

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        self._dispatchers = [
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{WebSocketNotification.SOUND_SETTINGS}",
                self._update_sound_settings,
            ),
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{CONNECTION_STATUS}",
                self._update_connection_state,
            ),
        ]

    async def _update_sound_settings(self, data: SoundSettings) -> None:
        """Update sound settings."""
        self._sound_settings = data
        self._attr_native_value = self._sound_settings.adjustments.treble

        self.async_write_ha_state()


class BangOlufsenNumberBass(BangOlufsenNumber):
    """Bass Number."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Init the bass Number."""
        super().__init__(entry)

        number_range: range = range(-6, 6, 1)
        self._attr_native_min_value = float(number_range.start)
        self._attr_native_max_value = float(number_range.stop)
        self._attr_name = f"{self._name} Bass"
        self._attr_unique_id = f"{self._unique_id}-bass"
        self._attr_icon = "mdi:equalizer"
        self._attr_mode = NumberMode.SLIDER

    async def async_set_native_value(self, value: float) -> None:
        """Set the bass value."""
        self._client.set_sound_settings_adjustments_bass(
            bass=Bass(value=value), async_req=True
        )

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        self._dispatchers = [
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{WebSocketNotification.SOUND_SETTINGS}",
                self._update_sound_settings,
            ),
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{CONNECTION_STATUS}",
                self._update_connection_state,
            ),
        ]

    async def _update_sound_settings(self, data: SoundSettings) -> None:
        """Update sound settings."""
        self._sound_settings = data
        self._attr_native_value = self._sound_settings.adjustments.bass

        self.async_write_ha_state()
