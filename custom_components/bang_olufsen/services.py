"""Actions for the Bang & Olufsen integration."""

from enum import StrEnum
from typing import TYPE_CHECKING, cast

import probatio

from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.const import ATTR_COMMAND, ATTR_DEVICE_ID
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

if TYPE_CHECKING:
    from . import BeoConfigEntry


class BeoService(StrEnum):
    """Store keys for Bang & Olufsen services."""

    # Mozart
    ALLSTANDBY = "beolink_allstandby"
    EXPAND = "beolink_expand"
    JOIN = "beolink_join"
    LEADER_COMMAND = "beolink_leader_command"
    LEAVE = "beolink_leave"
    REBOOT = "reboot"
    SET_RELATIVE_VOLUME = "beolink_set_relative_volume"
    SET_VOLUME = "beolink_set_volume"
    UNEXPAND = "beolink_unexpand"

    # Halo
    HALO_CONFIGURATION = "halo_configuration"
    HALO_DISPLAY_PAGE = "halo_display_page"
    HALO_NOTIFICATION = "halo_notification"


class BeoServiceArgument(StrEnum):
    """Store keys for Bang & Olufsen service arguments."""

    # Mozart
    ALL_DISCOVERED = "all_discovered"
    JIDS = "beolink_jids"
    JID = "beolink_jid"
    PARAMETER = "parameter"
    SOURCE_ID = "source_id"
    VOLUME_LEVEL = "volume_level"

    # Halo
    BUTTON_ID = "button_id"
    PAGE_ID = "page_id"
    SUBTITLE = "subtitle"
    TITLE = "title"


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register Bang & Olufsen actions."""

    # Mozart (entity) services
    jid_regex = probatio.Match(
        r"(^\d{4})[.](\d{7})[.](\d{8})(@products\.bang-olufsen\.com)$"
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        BeoService.JOIN,
        entity_domain=MEDIA_PLAYER_DOMAIN,
        schema={
            probatio.Optional(BeoServiceArgument.JID): jid_regex,
            probatio.Optional(BeoServiceArgument.SOURCE_ID): probatio.In(
                BEOLINK_JOIN_SOURCES
            ),
        },
        func=f"async_{BeoService.JOIN}",
        supports_response=SupportsResponse.OPTIONAL,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        BeoService.EXPAND,
        entity_domain=MEDIA_PLAYER_DOMAIN,
        schema={
            probatio.Exclusive(
                BeoServiceArgument.ALL_DISCOVERED, "devices", ""
            ): cv.boolean,
            probatio.Exclusive(
                BeoServiceArgument.JIDS,
                "devices",
                "Define either specific Beolink JIDs or all discovered",
            ): probatio.All(
                probatio.EnsureList(),
                [jid_regex],
            ),
        },
        func=f"async_{BeoService.EXPAND}",
        supports_response=SupportsResponse.OPTIONAL,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        BeoService.UNEXPAND,
        entity_domain=MEDIA_PLAYER_DOMAIN,
        schema={
            probatio.Required(BeoServiceArgument.JIDS): probatio.All(
                probatio.EnsureList(),
                [jid_regex],
            ),
        },
        func=f"async_{BeoService.UNEXPAND}",
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        BeoService.LEAVE,
        entity_domain=MEDIA_PLAYER_DOMAIN,
        schema=None,
        func=f"async_{BeoService.LEAVE}",
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        BeoService.ALLSTANDBY,
        entity_domain=MEDIA_PLAYER_DOMAIN,
        schema=None,
        func=f"async_{BeoService.ALLSTANDBY}",
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        BeoService.SET_VOLUME,
        entity_domain=MEDIA_PLAYER_DOMAIN,
        schema={probatio.Required(BeoServiceArgument.VOLUME_LEVEL): cv.string},
        func=f"async_{BeoService.SET_VOLUME}",
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        BeoService.SET_RELATIVE_VOLUME,
        entity_domain=MEDIA_PLAYER_DOMAIN,
        schema={probatio.Required(BeoServiceArgument.VOLUME_LEVEL): cv.string},
        func=f"async_{BeoService.SET_RELATIVE_VOLUME}",
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        BeoService.LEADER_COMMAND,
        entity_domain=MEDIA_PLAYER_DOMAIN,
        schema={
            probatio.Required(ATTR_COMMAND): probatio.In(ACCEPTED_COMMANDS),
            probatio.Optional(BeoServiceArgument.PARAMETER): cv.string,
        },
        func=f"async_{BeoService.LEADER_COMMAND}",
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        BeoService.REBOOT,
        entity_domain=MEDIA_PLAYER_DOMAIN,
        schema=None,
        func=f"async_{BeoService.REBOOT}",
    )

    # Halo (device) actions
    uuid_regex = probatio.Match(
        r"^[0-9a-f]{8}[-][0-9a-f]{4}[-][0-9a-f]{4}[-][0-9a-f]{4}[-][0-9a-f]{12}$"
    )

    hass.services.async_register(
        DOMAIN,
        BeoService.HALO_CONFIGURATION,
        _async_halo_configuration,
        schema=probatio.Schema({probatio.Required(ATTR_DEVICE_ID): cv.string}),
        supports_response=SupportsResponse.ONLY,
    )

    hass.services.async_register(
        DOMAIN,
        BeoService.HALO_NOTIFICATION,
        _async_halo_notification,
        schema=probatio.Schema(
            {
                probatio.Required(ATTR_DEVICE_ID): cv.string,
                probatio.Required(BeoServiceArgument.TITLE): probatio.All(
                    probatio.Length(min=1, max=62),
                    cv.string,
                ),
                probatio.Required(BeoServiceArgument.SUBTITLE): probatio.All(
                    probatio.Length(min=1, max=256),
                    cv.string,
                ),
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        BeoService.HALO_DISPLAY_PAGE,
        _async_halo_display_page,
        schema=probatio.Schema(
            {
                probatio.Required(ATTR_DEVICE_ID): cv.string,
                probatio.Required(BeoServiceArgument.PAGE_ID): uuid_regex,
                probatio.Optional(BeoServiceArgument.BUTTON_ID): uuid_regex,
            }
        ),
    )


def _get_client[T](call: ServiceCall, typ: type[T]) -> T:
    """Get API client from ServiceCall."""
    device_id = str(call.data[ATTR_DEVICE_ID])

    device_registry = dr.async_get(call.hass)
    if (device := device_registry.async_get(device_id)) is None:
        raise ServiceValidationError(
            f"Unable to find device: {call.data[ATTR_DEVICE_ID]}"
        )

    entry_id = str(device.primary_config_entry)
    if (entry := call.hass.config_entries.async_get_entry(entry_id)) is None:
        raise ServiceValidationError(f"Invalid config entry id: {entry_id}")

    return cast(T, cast("BeoConfigEntry", entry).runtime_data.client)


def _async_halo_configuration(call: ServiceCall) -> ServiceResponse:
    """Get raw configuration for the Halo."""
    return cast(ServiceResponse, _get_client(call, Halo).configuration.to_dict())


async def _async_halo_notification(call: ServiceCall) -> None:
    """Send a notification to the Halo."""
    await _get_client(call, Halo).update(
        Update(
            update=UpdateNotification(
                title=call.data[BeoServiceArgument.TITLE],
                message=call.data[BeoServiceArgument.SUBTITLE],
            )
        )
    )


async def _async_halo_display_page(call: ServiceCall) -> None:
    """Display a page and button on a Halo."""

    kwargs = {"page_id": call.data[BeoServiceArgument.PAGE_ID]}
    if (button_id := call.data.get(BeoServiceArgument.BUTTON_ID)) is not None:
        kwargs["button_id"] = button_id

    await _get_client(call, Halo).update(Update(update=UpdateDisplayPage(**kwargs)))
