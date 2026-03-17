"""Actions for the Bang & Olufsen integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import voluptuous as vol

if TYPE_CHECKING:
    from . import BeoConfigEntry
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    service,
)

from .beoremote_halo.halo import Halo
from .beoremote_halo.models import Update, UpdateDisplayPage, UpdateNotification
from .const import ACCEPTED_COMMANDS, BEOLINK_JOIN_SOURCES, DOMAIN

# Mozart
SERVICE_BEOLINK_JOIN = "beolink_join"
SERVICE_BEOLINK_EXPAND = "beolink_expand"
SERVICE_BEOLINK_UNEXPAND = "beolink_unexpand"
SERVICE_BEOLINK_LEAVE = "beolink_leave"
SERVICE_BEOLINK_ALLSTANDBY = "beolink_allstandby"
SERVICE_BEOLINK_SET_VOLUME = "beolink_set_volume"
SERVICE_BEOLINK_SET_RELATIVE_VOLUME = "beolink_set_relative_volume"
SERVICE_BEOLINK_LEADER_COMMAND = "beolink_leader_command"
SERVICE_REBOOT = "reboot"

ATTR_BEOLINK_JID = "beolink_jid"
ATTR_SOURCE_ID = "source_id"
ATTR_ALL_DISCOVERED = "all_discovered"
ATTR_BEOLINK_JIDS = "beolink_jids"
ATTR_VOLUME_LEVEL = "volume_level"
ATTR_COMMAND = "command"
ATTR_PARAMETER = "parameter"

# Halo
SERVICE_HALO_CONFIGURATION = "halo_configuration"
SERVICE_HALO_NOTIFICATION = "halo_notification"
SERVICE_HALO_DISPLAY_PAGE = "halo_display_page"

ATTR_TITLE = "title"
ATTR_SUBTITLE = "subtitle"
ATTR_PAGE_ID = "page_id"
ATTR_BUTTON_ID = "button_id"


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register Bang & Olufsen actions."""

    # Mozart (entity) services
    jid_regex = vol.Match(
        r"(^\d{4})[.](\d{7})[.](\d{8})(@products\.bang-olufsen\.com)$"
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_BEOLINK_JOIN,
        entity_domain=MEDIA_PLAYER_DOMAIN,
        schema={
            vol.Optional(ATTR_BEOLINK_JID): jid_regex,
            vol.Optional(ATTR_SOURCE_ID): vol.In(BEOLINK_JOIN_SOURCES),
        },
        func=f"async_{SERVICE_BEOLINK_JOIN}",
        supports_response=SupportsResponse.OPTIONAL,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_BEOLINK_EXPAND,
        entity_domain=MEDIA_PLAYER_DOMAIN,
        schema={
            vol.Exclusive(ATTR_ALL_DISCOVERED, "devices", ""): cv.boolean,
            vol.Exclusive(
                ATTR_BEOLINK_JIDS,
                "devices",
                "Define either specific Beolink JIDs or all discovered",
            ): vol.All(
                cv.ensure_list,
                [jid_regex],
            ),
        },
        func=f"async_{SERVICE_BEOLINK_EXPAND}",
        supports_response=SupportsResponse.OPTIONAL,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_BEOLINK_UNEXPAND,
        entity_domain=MEDIA_PLAYER_DOMAIN,
        schema={
            vol.Required(ATTR_BEOLINK_JIDS): vol.All(
                cv.ensure_list,
                [jid_regex],
            ),
        },
        func=f"async_{SERVICE_BEOLINK_UNEXPAND}",
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_BEOLINK_LEAVE,
        entity_domain=MEDIA_PLAYER_DOMAIN,
        schema=None,
        func=f"async_{SERVICE_BEOLINK_LEAVE}",
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_BEOLINK_ALLSTANDBY,
        entity_domain=MEDIA_PLAYER_DOMAIN,
        schema=None,
        func=f"async_{SERVICE_BEOLINK_ALLSTANDBY}",
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_BEOLINK_SET_VOLUME,
        entity_domain=MEDIA_PLAYER_DOMAIN,
        schema={vol.Required(ATTR_VOLUME_LEVEL): cv.string},
        func=f"async_{SERVICE_BEOLINK_SET_VOLUME}",
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_BEOLINK_SET_RELATIVE_VOLUME,
        entity_domain=MEDIA_PLAYER_DOMAIN,
        schema={vol.Required(ATTR_VOLUME_LEVEL): cv.string},
        func=f"async_{SERVICE_BEOLINK_SET_RELATIVE_VOLUME}",
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_BEOLINK_LEADER_COMMAND,
        entity_domain=MEDIA_PLAYER_DOMAIN,
        schema={
            vol.Required(ATTR_COMMAND): vol.In(ACCEPTED_COMMANDS),
            vol.Optional(ATTR_PARAMETER): cv.string,
        },
        func=f"async_{SERVICE_BEOLINK_LEADER_COMMAND}",
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_REBOOT,
        entity_domain=MEDIA_PLAYER_DOMAIN,
        schema=None,
        func=f"async_{SERVICE_REBOOT}",
    )

    # Halo (device) actions
    uuid_regex = vol.Match(
        r"^[0-9a-f]{8}[-][0-9a-f]{4}[-][0-9a-f]{4}[-][0-9a-f]{4}[-][0-9a-f]{12}$"
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_HALO_CONFIGURATION,
        _async_halo_configuration,
        schema=vol.Schema({vol.Required(ATTR_DEVICE_ID): cv.string}),
        supports_response=SupportsResponse.ONLY,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_HALO_NOTIFICATION,
        _async_halo_notification,
        schema=vol.Schema(
            {
                vol.Required(ATTR_DEVICE_ID): cv.string,
                vol.Required(ATTR_TITLE): vol.All(
                    vol.Length(min=1, max=62),
                    cv.string,
                ),
                vol.Required(ATTR_SUBTITLE): vol.All(
                    vol.Length(min=1, max=256),
                    cv.string,
                ),
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_HALO_DISPLAY_PAGE,
        _async_halo_display_page,
        schema=vol.Schema(
            {
                vol.Required(ATTR_DEVICE_ID): cv.string,
                vol.Required(ATTR_PAGE_ID): uuid_regex,
                vol.Optional(ATTR_BUTTON_ID): uuid_regex,
            }
        ),
    )


def _get_halo_client(call: ServiceCall) -> Halo:
    """Get Halo client from ServiceCall."""
    device_id = str(call.data[ATTR_DEVICE_ID])

    device_registry = dr.async_get(call.hass)
    if (device := device_registry.async_get(device_id)) is None:
        raise ServiceValidationError(
            f"Unable to find device: {call.data[ATTR_DEVICE_ID]}"
        )

    entry_id = str(device.primary_config_entry)
    if (entry := call.hass.config_entries.async_get_entry(entry_id)) is None:
        raise ServiceValidationError(f"Invalid config entry id: {entry_id}")

    return cast(Halo, cast("BeoConfigEntry", entry).runtime_data.client)


def _async_halo_configuration(call: ServiceCall) -> ServiceResponse:
    """Get raw configuration for the Halo."""
    return cast(ServiceResponse, _get_halo_client(call).configuration.to_dict())


async def _async_halo_notification(call: ServiceCall) -> None:
    """Send a notification to the Halo."""
    await _get_halo_client(call).update(
        Update(
            update=UpdateNotification(
                title=call.data["title"],
                subtitle=call.data["subtitle"],
            )
        )
    )


async def _async_halo_display_page(call: ServiceCall) -> None:
    """Display a page and button on a Halo."""

    kwargs = {"page_id": call.data["page_id"]}
    if call.data.get("button_id") is not None:
        kwargs["button_id"] = call.data["button_id"]

    await _get_halo_client(call).update(Update(update=UpdateDisplayPage(**kwargs)))
