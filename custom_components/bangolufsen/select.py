"""Select entities for the Bang & Olufsen Mozart integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from mozart_api.models import ListeningModeProps

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONNECTION_STATUS,
    DOMAIN,
    HASS_SELECTS,
    BangOlufsenVariables,
    WebSocketNotification,
)

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=120)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Select entities from config entry."""
    entities = []

    # Add select entities.
    for select in hass.data[DOMAIN][config_entry.unique_id][HASS_SELECTS]:
        entities.append(select)

    async_add_entities(new_entities=entities, update_before_add=True)


class BangOlufsenSelect(BangOlufsenVariables, SelectEntity):
    """Select for Mozart settings."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Init the Select."""
        super().__init__(entry)

        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_should_poll = False
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


class BangOlufsenSelectSoundMode(BangOlufsenSelect):
    """Sound mode Select."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Init the sound mode select."""
        super().__init__(entry)

        self._attr_name = f"{self._name} Sound mode"
        self._attr_unique_id = f"{self._unique_id}-sound-mode"
        self._attr_icon = "mdi:sine-wave"

        self._sound_modes: dict[int, str] = {}
        self._initial_setup()

    def _initial_setup(self) -> None:
        """Get the available sound modes and setup Select functionality."""
        sound_modes = self._client.get_listening_mode_set(async_req=True).get()
        active_sound_mode = self._client.get_active_listening_mode(async_req=True).get()

        # Add the key to make the labels unique as well
        self._sound_modes = {x["id"]: f"{x['name']} - {x['id']}" for x in sound_modes}

        # Set available options and selected option.
        self._attr_options = list(self._sound_modes.values())

        # Temp fix for any invalid active sound mode
        try:
            self._attr_current_option = self._sound_modes[active_sound_mode.id]
        except KeyError:
            self._attr_current_option = None

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        self._dispatchers = [
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{CONNECTION_STATUS}",
                self._update_connection_state,
            ),
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{WebSocketNotification.ACTIVE_LISTENING_MODE}",
                self._update_sound_mode,
            ),
        ]

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        key = [x for x in self._sound_modes if self._sound_modes[x] == option][0]

        self._client.activate_listening_mode(id=key, async_req=True)

    async def _update_sound_mode(self, data: ListeningModeProps) -> None:
        """Update sound mode."""
        active_sound_mode = data
        self._attr_current_option = self._sound_modes[active_sound_mode.id]

        self.async_write_ha_state()
