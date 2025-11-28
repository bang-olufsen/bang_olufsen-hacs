"""Event entities for the Bang & Olufsen integration."""

from __future__ import annotations

from typing import cast

from mozart_api.models import PairedRemote

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.components.homeassistant import ServiceResponse
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MODEL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import HaloConfigEntry, MozartConfigEntry
from .beoremote_halo.models import Update, UpdateDisplayPage, UpdateNotification
from .const import (
    BEO_REMOTE_CONTROL_KEYS,
    BEO_REMOTE_KEY_EVENTS,
    BEO_REMOTE_KEYS,
    BEO_REMOTE_SUBMENU_CONTROL,
    BEO_REMOTE_SUBMENU_LIGHT,
    CONNECTION_STATUS,
    DEVICE_BUTTON_EVENTS,
    DOMAIN,
    HALO_SYSTEM_EVENTS,
    MANUFACTURER,
    MODEL_SUPPORT_MAP,
    MODEL_SUPPORT_PROXIMITY,
    PROXIMITY_EVENTS,
    BeoModel,
    WebsocketNotification,
)
from .entity import HaloEntity, MozartEntity
from .util import get_device_buttons, get_remotes, is_halo

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Sensor entities from config entry."""
    entities: list[BeoEvent] = []

    if is_halo(config_entry):
        entities.extend(await _get_halo_entities(config_entry))
    else:
        entities.extend(await _get_mozart_entities(hass, config_entry))

    async_add_entities(new_entities=entities)


class BeoEvent(EventEntity):
    """Base Event class."""

    _attr_entity_registry_enabled_default = False

    @callback
    def _async_handle_event(self, event: str) -> None:
        """Handle event."""
        self._trigger_event(event)
        self.async_write_ha_state()


# Mozart entities
class MozartEvent(MozartEntity, BeoEvent):
    """Base Mozart Event class."""

    def __init__(self, config_entry: MozartConfigEntry) -> None:
        """Init the Event."""
        super().__init__(config_entry)


async def _get_mozart_entities(
    hass: HomeAssistant,
    config_entry: MozartConfigEntry,
) -> list[MozartEvent]:
    """Get Mozart Event entities from config entry."""
    entities: list[MozartEvent] = []

    # Add physical "buttons"
    entities.extend(
        [
            MozartButtonEvent(config_entry, button_type)
            for button_type in get_device_buttons(config_entry.data[CONF_MODEL])
        ]
    )

    # Check if device supports proximity detection.
    if config_entry.data[CONF_MODEL] in MODEL_SUPPORT_MAP[MODEL_SUPPORT_PROXIMITY]:
        entities.append(MozartEventProximity(config_entry))

    # Check for connected Beoremote One
    remotes = await get_remotes(config_entry.runtime_data.client)

    for remote in remotes:
        # Add Light keys
        entities.extend(
            [
                MozartRemoteKeyEvent(
                    config_entry,
                    remote,
                    f"{BEO_REMOTE_SUBMENU_LIGHT}/{key_type}",
                )
                for key_type in BEO_REMOTE_KEYS
            ]
        )

        # Add Control keys
        entities.extend(
            [
                MozartRemoteKeyEvent(
                    config_entry,
                    remote,
                    f"{BEO_REMOTE_SUBMENU_CONTROL}/{key_type}",
                )
                for key_type in (*BEO_REMOTE_KEYS, *BEO_REMOTE_CONTROL_KEYS)
            ]
        )

    # If the remote is no longer available, then delete the device.
    # The remote may appear as being available to the device after it has been unpaired on the remote
    # As it has to be removed from the device on the app.

    device_registry = dr.async_get(hass)
    devices = device_registry.devices.get_devices_for_config_entry_id(
        config_entry.entry_id
    )
    for device in devices:
        if device.model == BeoModel.BEOREMOTE_ONE and device.serial_number not in {
            remote.serial_number for remote in remotes
        }:
            device_registry.async_update_device(
                device.id, remove_config_entry_id=config_entry.entry_id
            )

    return entities


class MozartButtonEvent(MozartEvent):
    """Event class for Button events."""

    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = DEVICE_BUTTON_EVENTS

    def __init__(self, config_entry: MozartConfigEntry, button_type: str) -> None:
        """Initialize Button."""
        super().__init__(config_entry)

        self._attr_unique_id = f"{self._unique_id}_{button_type}"

        # Make the native button name Home Assistant compatible
        self._attr_translation_key = button_type.lower()

        self._button_type = button_type

    async def async_added_to_hass(self) -> None:
        """Listen to WebSocket button events."""
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
                f"{DOMAIN}_{self._unique_id}_{WebsocketNotification.BUTTON}_{self._button_type}",
                self._async_handle_event,
            )
        )


class MozartRemoteKeyEvent(MozartEvent):
    """Event class for Beoremote One key events."""

    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = BEO_REMOTE_KEY_EVENTS

    def __init__(
        self,
        config_entry: MozartConfigEntry,
        remote: PairedRemote,
        key_type: str,
    ) -> None:
        """Initialize Beoremote One key."""
        super().__init__(config_entry)

        assert remote.serial_number

        self._attr_unique_id = f"{remote.serial_number}_{self._unique_id}_{key_type}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{remote.serial_number}_{self._unique_id}")},
            name=f"{BeoModel.BEOREMOTE_ONE}-{remote.serial_number}-{self._unique_id}",
            model=BeoModel.BEOREMOTE_ONE,
            serial_number=remote.serial_number,
            sw_version=remote.app_version,
            manufacturer=MANUFACTURER,
            via_device=(DOMAIN, self._unique_id),
        )
        # Make the native key name Home Assistant compatible
        self._attr_translation_key = key_type.lower().replace("/", "_")

        self._key_type = key_type

    async def async_added_to_hass(self) -> None:
        """Listen to WebSocket Beoremote One key events."""
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
                f"{DOMAIN}_{self._unique_id}_{WebsocketNotification.BEO_REMOTE_BUTTON}_{self._key_type}",
                self._async_handle_event,
            )
        )


class MozartEventProximity(MozartEvent):
    """Event class for proximity sensor events."""

    _attr_device_class = EventDeviceClass.MOTION
    _attr_event_types = PROXIMITY_EVENTS
    _attr_translation_key = "proximity"

    def __init__(self, config_entry: MozartConfigEntry) -> None:
        """Init the proximity event."""
        super().__init__(config_entry)

        self._attr_unique_id = f"{self._unique_id}_proximity"

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
                f"{DOMAIN}_{self._unique_id}_{WebsocketNotification.PROXIMITY}",
                self._async_handle_event,
            )
        )


# Halo entities


class HaloEvent(HaloEntity, BeoEvent):
    """Base Halo Event class."""

    def __init__(self, config_entry: HaloConfigEntry) -> None:
        """Init the Event."""
        super().__init__(config_entry)


async def _get_halo_entities(
    config_entry: HaloConfigEntry,
) -> list[HaloEvent]:
    """Get Halo Event entities from config entry."""
    entities: list[HaloEvent] = [HaloEventSystemStatus(config_entry)]
    return entities


class HaloEventSystemStatus(HaloEvent):
    """Event class for Halo system status events."""

    _attr_entity_registry_enabled_default = True
    _attr_event_types = HALO_SYSTEM_EVENTS
    _attr_translation_key = "halo_system_status"

    def __init__(self, config_entry: HaloConfigEntry) -> None:
        """Init the system status event."""
        super().__init__(config_entry)

        self._attr_unique_id = f"{self._unique_id}_system_status"

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
                f"{DOMAIN}_{self._unique_id}_{WebsocketNotification.HALO_SYSTEM}",
                self._async_handle_event,
            )
        )

    # Setup custom actions
    def async_halo_configuration(self) -> ServiceResponse:
        """Get raw configuration for the Halo."""

        return cast(ServiceResponse, self._client.configuration.to_dict())

    async def async_halo_notification(self, title: str, subtitle: str) -> None:
        """Send a notification to the Halo."""

        await self._client.update(
            Update(
                update=UpdateNotification(
                    title=title,
                    subtitle=subtitle,
                )
            )
        )

    async def async_halo_display_page(
        self, page_id: str, button_id: str | None = None
    ) -> None:
        """Display a page and button on a Halo."""
        kwargs = {"page_id": page_id}
        if button_id is not None:
            kwargs["button_id"] = button_id

        await self._client.update(Update(update=UpdateDisplayPage(**kwargs)))
