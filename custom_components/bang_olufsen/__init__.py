"""The Bang & Olufsen integration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from aiohttp import ClientConnectorError, ClientOSError, ServerTimeoutError
from mozart_api.exceptions import ApiException
from mozart_api.mozart_client import MozartClient

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MODEL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.util.ssl import get_default_context

from .const import BEO_REMOTE_MODEL, DOMAIN
from .util import get_remote
from .websocket import BangOlufsenWebsocket

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.EVENT,
    Platform.MEDIA_PLAYER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.TEXT,
]


@dataclass
class BangOlufsenData:
    """Dataclass for API client, WebSocket listener and WebSocket initialization variables."""

    websocket: BangOlufsenWebsocket
    client: MozartClient
    platforms_initialized: int = 0


type BangOlufsenConfigEntry = ConfigEntry[BangOlufsenData]


def set_platform_initialized(data: BangOlufsenData) -> None:
    """Increment platforms_initialized to indicate that a platform has been initialized."""
    data.platforms_initialized += 1


async def _start_websocket_listener(data: BangOlufsenData) -> None:
    """Start WebSocket listener when all platforms have been initialized."""

    while True:
        # Check if all platforms have been initialized and start WebSocket listener
        if len(PLATFORMS) == data.platforms_initialized:
            break

        await asyncio.sleep(0)

    await data.client.connect_notifications(remote_control=True, reconnect=True)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: BangOlufsenConfigEntry
) -> bool:
    """Set up from a config entry."""

    # Remove casts to str
    assert config_entry.unique_id

    # Create device now as BangOlufsenWebsocket needs a device for debug logging, firing events etc.
    # And in order to ensure entity platforms (button, binary_sensor) have device name before the primary (media_player) is initialized
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, config_entry.unique_id)},
        name=config_entry.title,
        model=config_entry.data[CONF_MODEL],
    )

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
    ) as error:
        await client.close_api_client()
        raise ConfigEntryNotReady(
            f"Unable to connect to {config_entry.title}"
        ) from error

    # Initialize coordinator
    websocket = BangOlufsenWebsocket(hass, config_entry, client)

    # Add the coordinator and API client
    config_entry.runtime_data = BangOlufsenData(websocket, client)

    # Check for connected Beoremote One
    if remote := await get_remote(client):
        assert remote.serial_number

        # Create Beoremote One device
        assert config_entry.unique_id
        device_registry = dr.async_get(hass)
        device_registry.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            identifiers={(DOMAIN, remote.serial_number)},
            name=f"{BEO_REMOTE_MODEL} {remote.serial_number}",
            model=BEO_REMOTE_MODEL,
            serial_number=remote.serial_number,
            sw_version=remote.app_version,
            manufacturer="Bang & Olufsen",
            via_device=(DOMAIN, config_entry.unique_id),
        )
    else:
        # If the remote is no longer available, then delete the device.
        # The remote may appear as being available to the device after is has been unpaired on the remote
        # As it has to be removed from the device on the app.

        device_registry = dr.async_get(hass)
        devices = device_registry.devices.get_devices_for_config_entry_id(
            config_entry.entry_id
        )
        for device in devices:
            assert device.model is not None
            if device.model == BEO_REMOTE_MODEL:
                device_registry.async_remove_device(device.id)

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    # Start WebSocket connection when all entities have been initialized
    config_entry.async_create_background_task(
        hass,
        _start_websocket_listener(config_entry.runtime_data),
        f"{DOMAIN}-{config_entry.unique_id}-websocket_starter",
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant, config_entry: BangOlufsenConfigEntry
) -> bool:
    """Unload a config entry."""
    # Close the API client and WebSocket notification listener
    config_entry.runtime_data.client.disconnect_notifications()
    await config_entry.runtime_data.client.close_api_client()

    return await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
