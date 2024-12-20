"""Event entities for the Bang & Olufsen integration."""

from __future__ import annotations

from mozart_api.models import PairedRemote

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.const import CONF_MODEL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BangOlufsenConfigEntry, set_platform_initialized
from .const import (
    BEO_REMOTE_CONTROL_KEYS,
    BEO_REMOTE_KEY_EVENTS,
    BEO_REMOTE_KEYS,
    BEO_REMOTE_SUBMENU_CONTROL,
    BEO_REMOTE_SUBMENU_LIGHT,
    CONNECTION_STATUS,
    DEVICE_BUTTON_EVENTS,
    DEVICE_BUTTONS,
    DOMAIN,
    MODEL_SUPPORT_DEVICE_BUTTONS,
    MODEL_SUPPORT_MAP,
    MODEL_SUPPORT_PROXIMITY,
    PROXIMITY_EVENTS,
    WebsocketNotification,
)
from .entity import BangOlufsenEntity
from .util import get_remotes


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BangOlufsenConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sensor entities from config entry."""

    entities: list[BangOlufsenEvent] = []

    # Add physical "buttons"
    if config_entry.data[CONF_MODEL] in MODEL_SUPPORT_MAP[MODEL_SUPPORT_DEVICE_BUTTONS]:
        entities.extend(
            [
                BangOlufsenButtonEvent(config_entry, button_type)
                for button_type in DEVICE_BUTTONS
            ]
        )

    # Check if device supports proximity detection.
    if config_entry.data[CONF_MODEL] in MODEL_SUPPORT_MAP[MODEL_SUPPORT_PROXIMITY]:
        entities.append(BangOlufsenEventProximity(config_entry))

    # Check for connected Beoremote One
    if remotes := await get_remotes(config_entry.runtime_data.client):
        for remote in remotes:
            # Add Light keys
            entities.extend(
                [
                    BangOlufsenRemoteKeyEvent(
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
                    BangOlufsenRemoteKeyEvent(
                        config_entry,
                        remote,
                        f"{BEO_REMOTE_SUBMENU_CONTROL}/{key_type}",
                    )
                    for key_type in (*BEO_REMOTE_KEYS, *BEO_REMOTE_CONTROL_KEYS)
                ]
            )

    async_add_entities(new_entities=entities)

    set_platform_initialized(config_entry.runtime_data)


class BangOlufsenEvent(BangOlufsenEntity, EventEntity):
    """Base Event class."""

    _attr_entity_registry_enabled_default = False

    @callback
    def _async_handle_event(self, event: str) -> None:
        """Handle event."""
        self._trigger_event(event)
        self.async_write_ha_state()


class BangOlufsenButtonEvent(BangOlufsenEvent):
    """Event class for Button events."""

    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = DEVICE_BUTTON_EVENTS

    def __init__(self, config_entry: BangOlufsenConfigEntry, button_type: str) -> None:
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
                f"{self._unique_id}_{CONNECTION_STATUS}",
                self._async_update_connection_state,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{WebsocketNotification.BUTTON}_{self._button_type}",
                self._async_handle_event,
            )
        )


class BangOlufsenRemoteKeyEvent(BangOlufsenEvent):
    """Event class for Beoremote One key events."""

    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = BEO_REMOTE_KEY_EVENTS

    def __init__(
        self,
        config_entry: BangOlufsenConfigEntry,
        remote: PairedRemote,
        key_type: str,
    ) -> None:
        """Initialize Beoremote One key."""
        super().__init__(config_entry)

        assert remote.serial_number

        self._attr_unique_id = f"{remote.serial_number}_{key_type}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, remote.serial_number)}
        )
        # Make the native key name Home Assistant compatible
        self._attr_translation_key = key_type.lower().replace("/", "_")

        self._key_type = key_type

    async def async_added_to_hass(self) -> None:
        """Listen to WebSocket Beoremote One key events."""
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
                f"{self._unique_id}_{WebsocketNotification.BEO_REMOTE_BUTTON}_{self._key_type}",
                self._async_handle_event,
            )
        )


class BangOlufsenEventProximity(BangOlufsenEvent):
    """Event class for proximity sensor events."""

    _attr_device_class = EventDeviceClass.MOTION
    _attr_event_types = PROXIMITY_EVENTS
    _attr_translation_key = "proximity"

    def __init__(self, config_entry: BangOlufsenConfigEntry) -> None:
        """Init the proximity event."""
        super().__init__(config_entry)

        self._attr_unique_id = f"{self._unique_id}_proximity"

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
                f"{self._unique_id}_{WebsocketNotification.PROXIMITY}",
                self._async_handle_event,
            )
        )
