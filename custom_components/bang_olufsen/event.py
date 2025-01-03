"""Event entities for the Bang & Olufsen integration."""

from __future__ import annotations

from typing import cast

from mozart_api.models import PairedRemote
import voluptuous as vol

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.components.homeassistant import ServiceResponse
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MODEL
from homeassistant.core import HomeAssistant, SupportsResponse, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    async_get_current_platform,
)

from . import HaloConfigEntry, MozartConfigEntry, set_platform_initialized
from .const import (
    BEO_REMOTE_CONTROL_KEYS,
    BEO_REMOTE_KEY_EVENTS,
    BEO_REMOTE_KEYS,
    BEO_REMOTE_SUBMENU_CONTROL,
    BEO_REMOTE_SUBMENU_LIGHT,
    CONF_HALO,
    CONNECTION_STATUS,
    DEVICE_BUTTON_EVENTS,
    DEVICE_BUTTONS,
    DOMAIN,
    HALO_SYSTEM_EVENTS,
    MODEL_SUPPORT_DEVICE_BUTTONS,
    MODEL_SUPPORT_MAP,
    MODEL_SUPPORT_PROXIMITY,
    PROXIMITY_EVENTS,
    WebsocketNotification,
)
from .entity import HaloEntity, MozartEntity
from .halo import BaseUpdate, Notification, SystemEvent
from .util import get_remotes, is_halo


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sensor entities from config entry."""
    entities: list[BangOlufsenEvent] = []

    if is_halo(config_entry):
        # Register halo services

        platform = async_get_current_platform()

        platform.async_register_entity_service(
            name="halo_configuration",
            schema=None,
            func="async_halo_configuration",
            supports_response=SupportsResponse.ONLY,
        )

        platform.async_register_entity_service(
            name="halo_notification",
            schema={
                vol.Required("title"): vol.All(
                    vol.Length(min=1, max=62),
                    cv.string,
                ),
                vol.Required("subtitle"): vol.All(
                    vol.Length(min=1, max=256),
                    cv.string,
                ),
            },
            func="async_halo_notification",
        )

        entities.extend(await _get_halo_entities(config_entry))
    else:
        entities.extend(await _get_mozart_entities(config_entry))

    async_add_entities(new_entities=entities)

    set_platform_initialized(config_entry.runtime_data)


class BangOlufsenEvent(EventEntity):
    """Base Event class."""

    _attr_entity_registry_enabled_default = False

    @callback
    def _async_handle_event(self, event: str) -> None:
        """Handle event."""
        self._trigger_event(event)
        self.async_write_ha_state()


# Mozart entities


class BangOlufsenMozartEvent(MozartEntity, BangOlufsenEvent):
    """Base Mozart Event class."""

    def __init__(self, config_entry: MozartConfigEntry) -> None:
        """Init the Event."""
        super().__init__(config_entry)


async def _get_mozart_entities(
    config_entry: MozartConfigEntry,
) -> list[BangOlufsenMozartEvent]:
    """Get Mozart Event entities from config entry."""
    entities: list[BangOlufsenMozartEvent] = []

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

    return entities


class BangOlufsenButtonEvent(BangOlufsenMozartEvent):
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


class BangOlufsenRemoteKeyEvent(BangOlufsenMozartEvent):
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


class BangOlufsenEventProximity(BangOlufsenMozartEvent):
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


# Halo entities


class BangOlufsenHaloEvent(HaloEntity, BangOlufsenEvent):
    """Base Halo Event class."""

    def __init__(self, config_entry: HaloConfigEntry) -> None:
        """Init the Event."""
        super().__init__(config_entry)


async def _get_halo_entities(
    config_entry: HaloConfigEntry,
) -> list[BangOlufsenHaloEvent]:
    """Get Halo Event entities from config entry."""
    entities: list[BangOlufsenHaloEvent] = [BangOlufsenEventHaloSystem(config_entry)]
    return entities


class BangOlufsenEventHaloSystem(BangOlufsenHaloEvent):
    """Event class for Halo system events."""

    _attr_entity_registry_enabled_default = True
    _attr_event_types = HALO_SYSTEM_EVENTS
    _attr_translation_key = "halo_system"

    def __init__(self, config_entry: HaloConfigEntry) -> None:
        """Init the proximity event."""
        super().__init__(config_entry)

        self._attr_unique_id = f"{self._unique_id}_system"

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
                f"{self._unique_id}_{WebsocketNotification.HALO_SYSTEM}",
                self._update_system,
            )
        )

    @callback
    def _update_system(self, event: SystemEvent) -> None:
        """Handle system event."""
        self._trigger_event(event.state)
        self.async_write_ha_state()

    # Setup custom actions
    def async_halo_configuration(self) -> ServiceResponse:
        """Get raw configuration for the Halo."""

        return cast(ServiceResponse, self.entry.options[CONF_HALO])

    async def async_halo_notification(self, title: str, subtitle: str) -> None:
        """Send a notification to the Halo."""

        await self._client.send(
            BaseUpdate(
                update=Notification(
                    title=title,
                    subtitle=subtitle,
                )
            )
        )
