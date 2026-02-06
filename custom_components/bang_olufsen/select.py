"""Select entities for the Bang & Olufsen Mozart integration."""

from __future__ import annotations

import logging
from typing import cast
from uuid import UUID

from mozart_api.models import SpeakerGroupOverview
from mozart_api.mozart_client import MozartClient

from homeassistant.components.select import SelectEntity
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
    BeoPlatform,
    WebsocketNotification,
)
from .entity import BeoEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Select entities from config entry."""
    entities: list[BeoSelect] = []

    match BEO_MODEL_PLATFORM_MAP[config_entry.data[CONF_MODEL]]:
        case BeoPlatform.MOZART.value:
            # Create the listening position entity if supported
            scenes = await cast(
                MozartClient, config_entry.runtime_data.client
            ).get_all_scenes()

            for scene in scenes.values():
                if scene.tags is not None and "listeningposition" in scene.tags:
                    entities.append(BeoMozartListeningPosition(config_entry))
                    break

        case BeoPlatform.BEOREMOTE_HALO.value:
            pass

    async_add_entities(new_entities=entities)


class BeoSelect(SelectEntity, BeoEntity):
    """Base Select entity."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = []

    def __init__(self, config_entry: BeoConfigEntry) -> None:
        """Init the Select entity."""
        super().__init__(config_entry)


# Mozart entities


class BeoMozartListeningPosition(BeoSelect):
    """Listening position Select."""

    _attr_translation_key = "listening_position"

    def __init__(self, config_entry: BeoConfigEntry) -> None:
        """Init the listening position select."""
        super().__init__(config_entry)
        self._client: MozartClient

        self._attr_unique_id = f"{self._unique_id}_listening_position"
        self._attr_current_option = None

        self._listening_positions: dict[str, UUID] = {}
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
            scene_key_uuid = UUID(scene_key)
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
                        scene_key_uuid,
                    )
                    continue

                self._listening_positions[scene.label] = scene_key_uuid

                # Currently guess the current active listening position by the speakergroup ID
                if active_speaker_group.id == scene.action_list[0].speaker_group_id:
                    self._attr_current_option = scene.label

        self._attr_options = list(self._listening_positions)

        self.async_write_ha_state()
