"""Button entities for the Bang & Olufsen integration."""

from __future__ import annotations

from datetime import timedelta
from typing import cast

from mozart_api import StandStatus
from mozart_api.models import StandInfo, StandMovement
from mozart_api.mozart_client import MozartClient

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MODEL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BeoConfigEntry
from .const import BEO_MODEL_PLATFORM_MAP, DOMAIN, BeoPlatform
from .entity import BeoEntity
from .util import get_stand_info_and_status

SCAN_INTERVAL = timedelta(minutes=15)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Button entities from config entry."""
    entities: list[BeoNumber] = []

    match BEO_MODEL_PLATFORM_MAP[config_entry.data[CONF_MODEL]]:
        case BeoPlatform.MOZART.value:
            # Check for connected stands
            if stand := await get_stand_info_and_status(
                config_entry.runtime_data.client
            ):
                entities.append(BeoMozartStandStop(config_entry, stand))

        case BeoPlatform.BEOREMOTE_HALO.value:
            pass

    async_add_entities(new_entities=entities, update_before_add=True)


class BeoNumber(ButtonEntity, BeoEntity):
    """Base Bang & Olufsen Button."""

    def __init__(self, config_entry: BeoConfigEntry) -> None:
        """Initialize Button."""
        super().__init__(config_entry)


class BeoMozartStandStop(BeoNumber):
    """Motorized stand angle."""

    _attr_translation_key = "stand_stop"

    def __init__(
        self, config_entry: BeoConfigEntry, stand: tuple[StandInfo, StandStatus]
    ) -> None:
        """Init the stand stop Button."""
        super().__init__(config_entry)
        self._client: MozartClient

        stand_info, _ = stand

        self._attr_unique_id = f"{stand_info.serial_number}_stand_stop"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, cast(str, stand_info.serial_number))}
        )

    async def async_press(self) -> None:
        """Stop any ongoing stand movement."""
        await self._client.set_stand_movement(StandMovement(stand_motion="stop"))
