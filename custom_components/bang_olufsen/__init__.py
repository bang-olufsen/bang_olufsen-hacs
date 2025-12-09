"""The Bang & Olufsen integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from aiohttp import (
    ClientConnectorError,
    ClientOSError,
    ServerTimeoutError,
    WSMessageTypeError,
)
from mozart_api.exceptions import ApiException
from mozart_api.mozart_client import MozartClient

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MODEL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.typing import ConfigType
from homeassistant.util.ssl import get_default_context

from .beoremote_halo.halo import Halo
from .beoremote_halo.models import BaseConfiguration
from .const import CONF_HALO, DOMAIN, MANUFACTURER
from .services import async_setup_services
from .util import is_halo, is_mozart
from .websocket import HaloWebsocket, MozartWebsocket

MOZART_PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.EVENT,
    Platform.MEDIA_PLAYER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.TEXT,
]

HALO_PLATFORMS = [
    Platform.EVENT,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]


@dataclass
class MozartData:
    """Dataclass for Mozart API client, WebSocket listener and WebSocket initialization variables."""

    websocket: MozartWebsocket
    client: MozartClient


@dataclass
class HaloData:
    """Dataclass for API client, WebSocket listener and WebSocket initialization variables."""

    websocket: HaloWebsocket
    client: Halo


type MozartConfigEntry = ConfigEntry[MozartData]
type HaloConfigEntry = ConfigEntry[HaloData]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Bang & Olufsen integration."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up from a config entry."""

    # Remove casts to str
    assert config_entry.unique_id

    # Create device now as MozartWebsocket needs a device for debug logging, firing events etc.
    # And in order to ensure entity platforms (button, binary_sensor) have device name before the primary (media_player) is initialized
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, config_entry.unique_id)},
        name=config_entry.title,
        model=config_entry.data[CONF_MODEL],
        serial_number=config_entry.unique_id,
        manufacturer=MANUFACTURER,
    )

    if is_halo(config_entry):
        return await _setup_halo(hass, config_entry)

    if is_mozart(config_entry):
        return await _setup_mozart(hass, config_entry)

    return False


async def _setup_mozart(hass: HomeAssistant, config_entry: MozartConfigEntry) -> bool:
    """Set up a Mozart based product."""
    client = MozartClient(
        host=config_entry.data[CONF_HOST], ssl_context=get_default_context()
    )

    # Check API and WebSocket connection
    try:
        await client.check_device_connection(True)
    except* (
        ClientConnectorError,
        ClientOSError,
        ServerTimeoutError,
        ApiException,
        TimeoutError,
        WSMessageTypeError,
    ) as error:
        await client.close_api_client()
        raise ConfigEntryNotReady(
            f"Unable to connect to {config_entry.title}"
        ) from error

    # Initialize websocket
    websocket = MozartWebsocket(hass, config_entry, client)

    # Add the websocket and API client
    config_entry.runtime_data = MozartData(websocket, client)

    await hass.config_entries.async_forward_entry_setups(config_entry, MOZART_PLATFORMS)

    # Start WebSocket connection once the platforms have been loaded.
    # This ensures that the initial WebSocket notifications are dispatched to entities
    await client.connect_notifications(remote_control=True, reconnect=True)

    return True


async def _setup_halo(hass: HomeAssistant, config_entry: HaloConfigEntry) -> bool:
    """Set up a Halo."""

    # Get/set configuration
    if config_entry.options:
        client = Halo(
            config_entry.data[CONF_HOST],
            BaseConfiguration.from_dict(config_entry.options[CONF_HALO]),
        )
    else:
        client = Halo(config_entry.data[CONF_HOST])

    # Check WebSocket connection
    try:
        await client.check_device_connection(raise_error=True)
    except (
        ClientConnectorError,
        ClientOSError,
        ServerTimeoutError,
        WSMessageTypeError,
    ) as error:
        raise ConfigEntryNotReady(
            f"Unable to connect to {config_entry.title}"
        ) from error

    # Initialize websocket
    websocket = HaloWebsocket(hass, config_entry, client)

    # Add the websocket and API client
    config_entry.runtime_data = HaloData(websocket, client)

    await hass.config_entries.async_forward_entry_setups(config_entry, HALO_PLATFORMS)

    # Start WebSocket connection when all entities have been initialized
    await client.connect(reconnect=True)

    config_entry.async_on_unload(config_entry.add_update_listener(async_update_options))

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    # Close the API client and WebSocket notification listener
    if is_halo(config_entry):
        if TYPE_CHECKING:
            assert isinstance(config_entry.runtime_data, HaloData)

        await config_entry.runtime_data.client.disconnect()
        platforms = HALO_PLATFORMS
    elif is_mozart(config_entry):
        if TYPE_CHECKING:
            assert isinstance(config_entry.runtime_data, MozartData)

        config_entry.runtime_data.client.disconnect_notifications()
        await config_entry.runtime_data.client.close_api_client()
        platforms = MOZART_PLATFORMS

    return await hass.config_entries.async_unload_platforms(config_entry, platforms)
