"""Select entities for the Bang & Olufsen Mozart integration."""

from __future__ import annotations

import logging

from mozart_api.models import SpeakerGroupOverview

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MozartConfigEntry
from .const import CONNECTION_STATUS, DOMAIN, WebsocketNotification
from .entity import MozartEntity
from .util import is_halo, is_mozart

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Select entities from config entry."""
    entities: list[BeoSelect] = []

    if is_halo(config_entry):
        pass
    elif is_mozart(config_entry):
        entities.extend(await _get_mozart_entities(config_entry))

    async_add_entities(new_entities=entities)


class BeoSelect(SelectEntity):
    """Base Select entity."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = []


# Mozart entities
class MozartSelect(MozartEntity, BeoSelect):
    """Base Mozart Select class."""

    def __init__(self, config_entry: MozartConfigEntry) -> None:
        """Init the Select entity."""
        super().__init__(config_entry)


async def _get_mozart_entities(
    config_entry: MozartConfigEntry,
) -> list[MozartSelect]:
    """Get Mozart Select entities from config entry."""
    entities: list[MozartSelect] = []

    # Create the listening position entity if supported
    scenes = await config_entry.runtime_data.client.get_all_scenes()

    for scene in scenes.values():
        if scene.tags is not None and "listeningposition" in scene.tags:
            entities.append(MozartSelectListeningPosition(config_entry))
            break

    return entities


class MozartSelectListeningPosition(MozartSelect):
    """Listening position Select."""

    _attr_translation_key = "listening_position"

    def __init__(self, config_entry: MozartConfigEntry) -> None:
        """Init the listening position select."""
        super().__init__(config_entry)

        self._attr_unique_id = f"{self._unique_id}_listening_position"
        self._attr_current_option = None

        self._listening_positions: dict[str, str] = {}
        self._scenes: dict[str, str] = {}

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self._unique_id}_{CONNECTION_STATUS}",
                self._async_update_connection_state,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self._unique_id}_{WebsocketNotification.ACTIVE_SPEAKER_GROUP}",
                self._update_listening_positions,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self._unique_id}_{WebsocketNotification.REMOTE_MENU_CHANGED}",
                self._update_listening_positions,
            )
        )

        await self._update_listening_positions()

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self._client.post_scene_trigger(id=self._listening_positions[option])

    async def _update_listening_positions(
        self, active_speaker_group: SpeakerGroupOverview | None = None
    ) -> None:
        """Update listening position."""
        scenes = await self._client.get_all_scenes()

        if active_speaker_group is None:
            active_speaker_group = await self._client.get_speakergroup_active()

        self._listening_positions = {}

        # Listening positions
        for scene_key in scenes:
            scene = scenes[scene_key]

            if (
                scene.tags is not None
                and "listeningposition" in scene.tags
                and scene.label is not None
            ):
                # Ignore listening positions with the same name
                if scene.label in self._listening_positions:
                    _LOGGER.warning(
                        "Ignoring listening position with duplicate name: %s and ID: %s",
                        scene.label,
                        scene_key,
                    )
                    continue

                self._listening_positions[scene.label] = scene_key

                # Currently guess the current active listening position by the speakergroup ID
                if active_speaker_group.id == scene.action_list[0].speaker_group_id:
                    self._attr_current_option = scene.label

        self._attr_options = list(self._listening_positions)

        self.async_write_ha_state()
