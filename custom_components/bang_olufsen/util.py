"""Various utilities for the Bang & Olufsen integration."""

from __future__ import annotations

from typing import cast

from mozart_api.models import PairedRemote
from mozart_api.mozart_client import MozartClient


def get_serial_number_from_jid(jid: str) -> str:
    """Get serial number from Beolink JID."""
    return jid.split(".")[2].split("@")[0]


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
