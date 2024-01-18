"""Button entities for the Bang & Olufsen integration."""


from __future__ import annotations

from typing import cast

from mozart_api.models import Preset

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BangOlufsenData
from .const import CONNECTION_STATUS, DOMAIN, SOURCE_ENUM
from .entity import BangOlufsenEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Button entities from config entry."""
    data: BangOlufsenData = hass.data[DOMAIN][config_entry.entry_id]
    entities: list[BangOlufsenButton] = []

    # Get available favourites from coordinator.
    favourites = data.coordinator.data.favourites

    entities.extend(
        [
            BangOlufsenButtonFavourite(config_entry, data, favourites[favourite])
            for favourite in favourites
        ]
    )

    async_add_entities(new_entities=entities)


class BangOlufsenButton(ButtonEntity, BangOlufsenEntity):
    """Base Button class."""


class BangOlufsenButtonFavourite(CoordinatorEntity, BangOlufsenButton):
    """Favourite Button."""

    def __init__(
        self,
        entry: ConfigEntry,
        data: BangOlufsenData,
        favourite: Preset,
    ) -> None:
        """Init a favourite Button."""
        CoordinatorEntity.__init__(self, data.coordinator)
        BangOlufsenButton.__init__(self, entry, data.client)

        self._favourite_id: int = int(cast(str, favourite.name)[6:])
        self._favourite: Preset = favourite

        self._attr_name = f"Favourite {self._favourite_id}"
        self._attr_unique_id = f"{self._unique_id}-favourite-{self._favourite_id}"

        if self._favourite_id in range(10):
            self._attr_icon = f"mdi:numeric-{self._favourite_id}-box"
        else:
            self._attr_icon = "mdi:numeric-9-plus-box"

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        await super().async_added_to_hass()

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{CONNECTION_STATUS}",
                self._update_connection_state,
            )
        )

        self.async_on_remove(
            self.coordinator.async_add_listener(self._update_favourite)
        )

        self._attr_extra_state_attributes = self._generate_favourite_attributes()

    async def async_press(self) -> None:
        """Handle the action."""
        await self._client.activate_preset(id=self._favourite_id)

    @callback
    def _update_favourite(self) -> None:
        """Update favourite attribute."""
        self._favourite = self.coordinator.data.favourites[str(self._favourite_id)]

        self._attr_extra_state_attributes = self._generate_favourite_attributes()

        self.async_write_ha_state()

    def _generate_favourite_attributes(
        self,
    ) -> dict[str, str | int | dict[str, str | bool]]:
        """Generate extra state attributes for a favourite."""
        favourite_attribute: dict[str, str | int | dict[str, str | bool]] = {}

        # Ensure that favourites with volume are properly shown.
        if self._favourite.action_list:
            for action in self._favourite.action_list:
                if action.type == "volume":
                    favourite_attribute["volume"] = action.volume_level

                else:
                    deezer_user_id = action.deezer_user_id
                    favourite_type = action.type
                    favourite_queue = action.queue_item

                    # Add Deezer as "source".
                    if (
                        favourite_type == "deezerFlow"
                        or favourite_type == "playQueue"
                        and favourite_queue.provider.value == "deezer"
                    ):
                        favourite_attribute["source"] = SOURCE_ENUM.deezer

                    # Add netradio as "source".
                    elif favourite_type == "radio":
                        favourite_attribute["source"] = SOURCE_ENUM.netRadio

                    # Add the source name if it is not none.
                    elif self._favourite.source and self._favourite.source.value:
                        favourite_attribute["source"] = SOURCE_ENUM[
                            self._favourite.source.value
                        ].value

                    # Add title if available.
                    if self._favourite.title:
                        favourite_attribute["name"] = self._favourite.title

                    # Ensure that all favourites have a "name".
                    if "name" not in favourite_attribute:
                        favourite_attribute["name"] = favourite_attribute["source"]

                    # Add Deezer flow.
                    if favourite_type == "deezerFlow":
                        if deezer_user_id:
                            favourite_attribute["id"] = int(deezer_user_id)

                    # Add Deezer playlist "uri" and name
                    elif favourite_type == "playQueue":
                        favourite_attribute["id"] = favourite_queue.uri

                        # Add queue settings for Deezer queues.
                        if action.queue_settings:
                            favourite_attribute["queue_settings"] = {
                                "repeat": action.queue_settings.repeat,
                                "shuffle": action.queue_settings.shuffle,
                            }

        return favourite_attribute
