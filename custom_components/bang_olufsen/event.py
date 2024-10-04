"""Event entities for the Bang & Olufsen integration."""

from __future__ import annotations

from mozart_api.models import PairedRemote
from mozart_api.mozart_client import MozartClient

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MODEL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    BEO_REMOTE_CONTROL_KEYS,
    BEO_REMOTE_KEY_EVENTS,
    BEO_REMOTE_KEYS,
    BEO_REMOTE_LIGHT_KEYS,
    BEO_REMOTE_SUBMENU_CONTROL,
    BEO_REMOTE_SUBMENU_LIGHT,
    CONNECTION_STATUS,
    DEVICE_BUTTON_EVENTS,
    DEVICE_BUTTONS,
    DOMAIN,
    MODEL_SUPPORT_DEVICE_CONTROLS,
    MODEL_SUPPORT_MAP,
    MODEL_SUPPORT_PROXIMITY,
    PROXIMITY_EVENTS,
    WebsocketNotification,
)
from .entity import BangOlufsenEntity
from .util import BangOlufsenData, get_remote, set_platform_initialized


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sensor entities from config entry."""
    data: BangOlufsenData = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[EventEntity] = []

    # Add physical "buttons"
    if (
        config_entry.data[CONF_MODEL]
        in MODEL_SUPPORT_MAP[MODEL_SUPPORT_DEVICE_CONTROLS]
    ):
        entities.extend(
            [
                BangOlufsenButtonEvent(config_entry, data.client, button_type)
                for button_type in DEVICE_BUTTONS
            ]
        )

    # Check if device supports proximity detection.
    if config_entry.data[CONF_MODEL] in MODEL_SUPPORT_MAP[MODEL_SUPPORT_PROXIMITY]:
        entities.append(BangOlufsenEventProximity(config_entry, data.client))

    # Check for connected Beoremote One
    if remote := await get_remote(data.client):
        # Add Light keys
        entities.extend(
            [
                BangOlufsenRemoteKeyEvent(
                    config_entry,
                    data.client,
                    remote,
                    f"{BEO_REMOTE_SUBMENU_LIGHT}/{key_type}",
                )
                for key_type in (*BEO_REMOTE_KEYS, *BEO_REMOTE_LIGHT_KEYS)
            ]
        )

        # Add Control keys
        entities.extend(
            [
                BangOlufsenRemoteKeyEvent(
                    config_entry,
                    data.client,
                    remote,
                    f"{BEO_REMOTE_SUBMENU_CONTROL}/{key_type}",
                )
                for key_type in (*BEO_REMOTE_KEYS, *BEO_REMOTE_CONTROL_KEYS)
            ]
        )

    async_add_entities(new_entities=entities)

    set_platform_initialized(data)


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
    _attr_icon = "mdi:gesture-tap-button"

    def __init__(
        self, entry: ConfigEntry, client: MozartClient, button_type: str
    ) -> None:
        """Initialize Button."""
        super().__init__(entry, client)

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
    _attr_icon = "mdi:remote"

    def __init__(
        self,
        entry: ConfigEntry,
        client: MozartClient,
        remote: PairedRemote,
        key_type: str,
    ) -> None:
        """Initialize Beoremote One key."""
        super().__init__(entry, client)
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
    _attr_icon = "mdi:account-question"
    _attr_translation_key = "proximity"

    def __init__(self, entry: ConfigEntry, client: MozartClient) -> None:
        """Init the proximity event."""
        super().__init__(entry, client)

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
