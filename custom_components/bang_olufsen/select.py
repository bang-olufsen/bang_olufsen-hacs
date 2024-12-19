"""Select entities for the Bang & Olufsen Mozart integration."""

from __future__ import annotations

import logging

from mozart_api.models import SpeakerGroupOverview

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BangOlufsenConfigEntry, set_platform_initialized
from .const import CONNECTION_STATUS, WebsocketNotification
from .entity import BangOlufsenEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BangOlufsenConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Select entities from config entry."""
    entities: list[BangOlufsenSelect] = []

    # Create the listening position entity if supported
    scenes = await config_entry.runtime_data.client.get_all_scenes()

    for scene in scenes.values():
        if scene.tags is not None and "listeningposition" in scene.tags:
            entities.append(BangOlufsenSelectListeningPosition(config_entry))
            break

    async_add_entities(new_entities=entities)

    set_platform_initialized(config_entry.runtime_data)


class BangOlufsenSelect(BangOlufsenEntity, SelectEntity):
    """Select for Mozart settings."""

    def __init__(self, config_entry: BangOlufsenConfigEntry) -> None:
        """Init the Select."""
        super().__init__(config_entry)

        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_current_option = None
        self._attr_options = []


class BangOlufsenSelectListeningPosition(BangOlufsenSelect):
    """Listening position Select."""

    _attr_translation_key = "listening_position"

    def __init__(self, config_entry: BangOlufsenConfigEntry) -> None:
        """Init the listening position select."""
        super().__init__(config_entry)

        self._attr_unique_id = f"{self._unique_id}-listening-position"

        self._listening_positions: dict[str, str] = {}
        self._scenes: dict[str, str] = {}

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
                f"{self._unique_id}_{WebsocketNotification.ACTIVE_SPEAKER_GROUP}",
                self._update_listening_positions,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{WebsocketNotification.REMOTE_MENU_CHANGED}",
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
                if scene.label is not None:
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
