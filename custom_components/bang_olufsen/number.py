"""Number entities for the Bang & Olufsen integration."""

from __future__ import annotations

from datetime import timedelta
from typing import cast

from mozart_api import StandStatus
from mozart_api.models import StandInfo, StandMovement, StandPosition
from mozart_api.mozart_client import MozartClient, WebSocketEventTypes

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MODEL, DEGREE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BeoConfigEntry
from .const import BEO_MODEL_PLATFORM_MAP, CONNECTION_STATUS, DOMAIN, BeoPlatform
from .entity import BeoEntity
from .util import get_stand_info_and_status

SCAN_INTERVAL = timedelta(minutes=15)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Number entities from config entry."""
    entities: list[BeoNumber] = []

    match BEO_MODEL_PLATFORM_MAP[config_entry.data[CONF_MODEL]]:
        case BeoPlatform.MOZART.value:
            # Check for connected stands
            if stand := await get_stand_info_and_status(
                config_entry.runtime_data.client
            ):
                entities.append(BeoMozartStandAngle(config_entry, stand))

        case BeoPlatform.BEOREMOTE_HALO.value:
            pass

    async_add_entities(new_entities=entities, update_before_add=True)


class BeoNumber(NumberEntity, BeoEntity):
    """Base Bang & Olufsen Number."""

    def __init__(self, config_entry: BeoConfigEntry) -> None:
        """Initialize Number."""
        super().__init__(config_entry)


class BeoMozartStandAngle(BeoNumber):
    """Motorized stand angle."""

    _attr_native_min_value = 0
    _attr_native_max_value = 110
    _attr_native_unit_of_measurement = DEGREE
    _attr_translation_key = "stand_angle"

    def __init__(
        self, config_entry: BeoConfigEntry, stand: tuple[StandInfo, StandStatus]
    ) -> None:
        """Init the stand angle Number."""
        super().__init__(config_entry)
        self._client: MozartClient

        self._stand_info, self._stand_status = stand

        self._attr_unique_id = f"{self._stand_info.serial_number}_stand_angle"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, cast(str, self._stand_info.serial_number))}
        )

        self._attr_native_value = cast(StandPosition, self._stand_status.position).angle

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
                f"{DOMAIN}_{self._unique_id}_{WebSocketEventTypes.STAND_POSITION}",
                self._update_angle,
            )
        )

    async def _update_angle(self, data: StandPosition) -> None:
        """Update Number value."""
        # Round the number, as the supplied angle has many digits
        self._attr_native_value = round(cast(float, data.angle), 2)
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Set the angle of the stand."""
        await self._client.set_stand_movement(StandMovement(angle=value))
