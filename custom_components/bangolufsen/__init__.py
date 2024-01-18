"""The Bang & Olufsen integration."""
from __future__ import annotations

from dataclasses import dataclass

from aiohttp.client_exceptions import ClientConnectorError
from mozart_api.exceptions import ApiException
from mozart_api.mozart_client import MozartClient

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MODEL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .coordinator import BangOlufsenCoordinator


@dataclass
class BangOlufsenData:
    """Dataclass for API client and coordinator containing WebSocket client."""

    coordinator: DataUpdateCoordinator
    client: MozartClient


PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.MEDIA_PLAYER,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TEXT,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    # Remove casts to str
    assert entry.unique_id

    device_registry = dr.async_get(hass)

    # Create device in order to ensure entity platforms (button, binary_sensor)
    # have device name before the primary (media_player) is initialized
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.unique_id)},
        name=entry.title,
        model=entry.data[CONF_MODEL],
    )

    client = MozartClient(host=entry.data[CONF_HOST], websocket_reconnect=True)

    # Check connection and try to initialize it.
    try:
        await client.get_battery_state(_request_timeout=3)
    except (ApiException, ClientConnectorError, TimeoutError) as error:
        await client.close_api_client()
        raise ConfigEntryNotReady(f"Unable to connect to {entry.title}") from error

    coordinator = BangOlufsenCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = BangOlufsenData(
        coordinator=coordinator,
        client=client,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    client.connect_notifications()

    entry.async_on_unload(entry.add_update_listener(update_listener))

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


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
