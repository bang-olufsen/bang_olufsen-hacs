"""Various utilities for the Bang & Olufsen integration."""

from __future__ import annotations

import logging
from typing import cast

from mozart_api import __version__ as MOZART_API_VERSION
from mozart_api.models import PairedRemote, Source
from mozart_api.mozart_client import MozartClient

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MODEL

from .const import FALLBACK_SOURCES, MOZART_MODELS, BangOlufsenModel

_LOGGER = logging.getLogger(__name__)


def get_serial_number_from_jid(jid: str) -> str:
    """Get serial number from Beolink JID."""
    return jid.split(".")[2].split("@")[0]


def is_halo(config_entry: ConfigEntry) -> bool:
    """Return if device is a Halo."""

    if config_entry.data[CONF_MODEL] == BangOlufsenModel.BEOREMOTE_HALO:
        return True
    return False


def is_mozart(config_entry: ConfigEntry) -> bool:
    """Return if device is Mozart based."""

    if config_entry.data[CONF_MODEL] in MOZART_MODELS:
        return True
    return False


async def supports_battery(client: MozartClient) -> bool:
    """Get if a Mozart device has a battery."""
    battery_state = await client.get_battery_state()

    return bool(battery_state.battery_level and battery_state.battery_level > 0)


async def get_remotes(client: MozartClient) -> list[PairedRemote]:
    """Get remote status easier."""
    # Get if a remote control is connected and the remote
    bluetooth_remote_list = await client.get_bluetooth_remotes()

    # Remotes that been unpaired on the remote may still be available on the device,
    # But should not be treated as available.
    return [
        remote
        for remote in cast(list[PairedRemote], bluetooth_remote_list.items)
        if remote.serial_number is not None
    ]


async def get_sources(client: MozartClient) -> list[Source]:
    """Ensure sources received, even when the API client is outdated."""
    try:
        return cast(
            list[Source],
            (await client.get_available_sources(target_remote=False)).items,
        )
    except ValueError:
        _LOGGER.warning(
            "The API client: %s is outdated compared to the device software. Using fallback sources",
            MOZART_API_VERSION,
        )
        return FALLBACK_SOURCES
