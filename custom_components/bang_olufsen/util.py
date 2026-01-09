"""Various utilities for the Bang & Olufsen integration."""

from __future__ import annotations

import logging
from typing import cast

from mozart_api import __version__ as MOZART_API_VERSION
from mozart_api.models import PairedRemote, Source
from mozart_api.mozart_client import MozartClient

from .beoremote_halo import Halo
from .const import (
    BEO_REMOTE_CONTROL_KEYS,
    BEO_REMOTE_KEYS,
    BEO_REMOTE_SUBMENU_CONTROL,
    BEO_REMOTE_SUBMENU_LIGHT,
    DEVICE_BUTTONS,
    FALLBACK_SOURCES,
    BeoButtons,
    BeoModel,
)

_LOGGER = logging.getLogger(__name__)


def get_serial_number_from_jid(jid: str) -> str:
    """Get serial number from Beolink JID."""
    return jid.split(".")[2].split("@")[0]


async def get_remotes(client: MozartClient | Halo) -> list[PairedRemote]:
    """Get paired remotes."""
    bluetooth_remote_list = await cast(MozartClient, client).get_bluetooth_remotes()

    # Remotes that been unpaired on the remote may still be available on the device,
    # But should not be treated as available.
    return [
        remote
        for remote in cast(list[PairedRemote], bluetooth_remote_list.items)
        if remote.serial_number is not None
    ]


async def get_sources(client: MozartClient | Halo) -> list[Source]:
    """Ensure sources received, even when the API client is outdated."""
    try:
        return cast(
            list[Source],
            (
                await cast(MozartClient, client).get_available_sources(
                    target_remote=False
                )
            ).items,
        )
    except ValueError:
        _LOGGER.warning(
            "The API client: %s is outdated compared to the device software. Using fallback sources",
            MOZART_API_VERSION,
        )
        return FALLBACK_SOURCES


def get_device_buttons(model: BeoModel) -> list[str]:
    """Get supported buttons for a given model."""
    # Beoconnect Core does not have any buttons
    if model == BeoModel.BEOCONNECT_CORE:
        return []

    buttons = DEVICE_BUTTONS.copy()

    # Models that don't have a microphone button
    if model in (
        BeoModel.BEOSOUND_A5,
        BeoModel.BEOSOUND_A9,
        BeoModel.BEOSOUND_PREMIERE,
    ):
        buttons.remove(BeoButtons.MICROPHONE)

    # Models that don't have a Bluetooth button
    if model in (
        BeoModel.BEOSOUND_A9,
        BeoModel.BEOSOUND_PREMIERE,
    ):
        buttons.remove(BeoButtons.BLUETOOTH)

    return buttons


def get_remote_keys() -> list[str]:
    """Get remote keys for the Beoremote One. Formatted for Home Assistant use."""
    return [
        *[f"{BEO_REMOTE_SUBMENU_LIGHT}/{key_type}" for key_type in BEO_REMOTE_KEYS],
        *[
            f"{BEO_REMOTE_SUBMENU_CONTROL}/{key_type}"
            for key_type in (*BEO_REMOTE_KEYS, *BEO_REMOTE_CONTROL_KEYS)
        ],
    ]


async def supports_battery(client: MozartClient | Halo) -> bool:
    """Get if a Mozart device has a battery."""
    battery_state = await cast(MozartClient, client).get_battery_state()

    return bool(battery_state.battery_level and battery_state.battery_level > 0)
