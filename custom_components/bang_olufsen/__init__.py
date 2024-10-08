"""The Bang & Olufsen integration."""

from __future__ import annotations

import asyncio

from aiohttp import ClientConnectorError, ClientOSError, ServerTimeoutError
from mozart_api.exceptions import ApiException
from mozart_api.mozart_client import MozartClient

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MODEL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.util.ssl import get_default_context

from .const import DOMAIN
from .coordinator import BangOlufsenCoordinator
from .util import BangOlufsenData, get_remote

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.EVENT,
    Platform.MEDIA_PLAYER,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TEXT,
]


async def _start_websocket_listener(data: BangOlufsenData) -> None:
    """Start WebSocket listener when all platforms have been initialized."""

    while True:
        # Check if all platforms have been initialized and start WebSocket listener
        if len(PLATFORMS) == data.platforms_initialized:
            break

        await asyncio.sleep(0)

    await data.client.connect_notifications(remote_control=True, reconnect=True)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""

    # Remove casts to str
    assert entry.unique_id

    # Create device now as BangOlufsenWebsocket needs a device for debug logging, firing events etc.
    # And in order to ensure entity platforms (button, binary_sensor) have device name before the primary (media_player) is initialized
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.unique_id)},
        name=entry.title,
        model=entry.data[CONF_MODEL],
    )

    client = MozartClient(host=entry.data[CONF_HOST], ssl_context=get_default_context())

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
        raise ConfigEntryNotReady(f"Unable to connect to {entry.title}") from error

    # Initialize coordinator
    coordinator = BangOlufsenCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    # Add the coordinator and API client
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = BangOlufsenData(
        coordinator,
        client,
    )

    # Check for connected Beoremote One
    if remote := await get_remote(client):
        assert remote.serial_number

        # Create Beoremote One device
        assert entry.unique_id
        device_registry = dr.async_get(hass)
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, remote.serial_number)},
            name=f"Beoremote One {remote.serial_number}",
            model="Beoremote One",
            serial_number=remote.serial_number,
            sw_version=remote.app_version,
            manufacturer="Bang & Olufsen",
            via_device=(DOMAIN, entry.unique_id),
        )
    else:
        # If the remote is no longer available, then delete the device.
        # The remote may appear as being available to the device after is has been unpaired on the remote
        # As it has to be removed from the device on the app.

        device_registry = dr.async_get(hass)
        devices = device_registry.devices.get_devices_for_config_entry_id(
            entry.entry_id
        )
        for device in devices:
            assert device.model is not None
            if device.model == "Beoremote One":
                device_registry.async_remove_device(device.id)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Start WebSocket connection when all entities have been initialized
    entry.async_create_background_task(
        hass,
        _start_websocket_listener(hass.data[DOMAIN][entry.entry_id]),
        f"{DOMAIN}-{entry.unique_id}-websocket_starter",
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Close the API client and WebSocket notification listener
    hass.data[DOMAIN][entry.entry_id].client.disconnect_notifications()
    await hass.data[DOMAIN][entry.entry_id].client.close_api_client()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
