"""Services for Bang & Olufsen."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.components.event import DOMAIN as EVENT_DOMAIN
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.core import HomeAssistant, SupportsResponse, callback
from homeassistant.helpers import config_validation as cv, service

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
    """Register Bang & Olufsen services."""

    # Mozart services
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

    # Halo services

    uuid_regex = vol.Match(
        r"^[0-9a-f]{8}[-][0-9a-f]{4}[-][0-9a-f]{4}[-][0-9a-f]{4}[-][0-9a-f]{12}$"
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_HALO_CONFIGURATION,
        entity_domain=EVENT_DOMAIN,
        schema=None,
        func=f"async_{SERVICE_HALO_CONFIGURATION}",
        supports_response=SupportsResponse.ONLY,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_HALO_NOTIFICATION,
        entity_domain=EVENT_DOMAIN,
        schema={
            vol.Required(ATTR_TITLE): vol.All(
                vol.Length(min=1, max=62),
                cv.string,
            ),
            vol.Required(ATTR_SUBTITLE): vol.All(
                vol.Length(min=1, max=256),
                cv.string,
            ),
        },
        func=f"async_{SERVICE_HALO_NOTIFICATION}",
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_HALO_DISPLAY_PAGE,
        entity_domain=EVENT_DOMAIN,
        schema={
            vol.Required(ATTR_PAGE_ID): uuid_regex,
            vol.Optional(ATTR_BUTTON_ID): uuid_regex,
        },
        func=f"async_{SERVICE_HALO_DISPLAY_PAGE}",
    )
