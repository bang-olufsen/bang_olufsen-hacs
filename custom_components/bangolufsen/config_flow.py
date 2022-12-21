"""Config flow for the Bang & Olufsen integration."""
from __future__ import annotations

import ipaddress
import logging
from typing import Any, TypedDict

from inflection import underscore
from mozart_api.exceptions import ApiException
from mozart_api.mozart_client import MozartClient
from urllib3.exceptions import MaxRetryError, NewConnectionError
import voluptuous as vol

from homeassistant.components.zeroconf import ZeroconfServiceInfo
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_FRIENDLY_NAME, CONF_HOST, CONF_MODEL, CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import AbortFlow, FlowResult
from homeassistant.helpers import config_validation as cv, selector

from .const import (
    API_EXCEPTION,
    ATTR_FRIENDLY_NAME,
    ATTR_ITEM_NUMBER,
    ATTR_SERIAL_NUMBER,
    ATTR_TYPE_NUMBER,
    COMPATIBLE_MODELS,
    CONF_BEOLINK_JID,
    CONF_DEFAULT_VOLUME,
    CONF_MAX_VOLUME,
    CONF_SERIAL_NUMBER,
    CONF_VOLUME_STEP,
    DEFAULT_DEFAULT_VOLUME,
    DEFAULT_HOST,
    DEFAULT_MAX_VOLUME,
    DEFAULT_MODEL,
    DEFAULT_NAME,
    DEFAULT_VOLUME_RANGE,
    DEFAULT_VOLUME_STEP,
    DOMAIN,
    MAX_RETRY_ERROR,
    MAX_VOLUME_RANGE,
    NEW_CONNECTION_ERROR,
    VALUE_ERROR,
    VOLUME_STEP_RANGE,
)

_LOGGER = logging.getLogger(__name__)


def _config_schema(
    name: str = DEFAULT_NAME,
    volume_step: int = DEFAULT_VOLUME_STEP,
    default_volume: int = DEFAULT_DEFAULT_VOLUME,
    max_volume: int = DEFAULT_MAX_VOLUME,
) -> dict:
    """Create a schema for configuring the device with adjustable default values."""
    return {
        vol.Optional(CONF_NAME, default=name): cv.string,
        vol.Required(CONF_VOLUME_STEP, default=volume_step): vol.All(
            vol.Coerce(int),
            vol.Range(
                min=VOLUME_STEP_RANGE.start,
                max=(VOLUME_STEP_RANGE.stop - 1),
            ),
        ),
        vol.Required(CONF_DEFAULT_VOLUME, default=default_volume): vol.All(
            vol.Coerce(int),
            vol.Range(
                min=DEFAULT_VOLUME_RANGE.start,
                max=(DEFAULT_VOLUME_RANGE.stop - 1),
            ),
        ),
        vol.Required(CONF_MAX_VOLUME, default=max_volume): vol.All(
            vol.Coerce(int),
            vol.Range(
                min=MAX_VOLUME_RANGE.start,
                max=(MAX_VOLUME_RANGE.stop - 1),
            ),
        ),
    }


async def _validate_host(host: str) -> tuple[str, str, str]:
    """Validate that a connection can be made to the device and return jid, friendly name and serial number."""
    try:
        # Check if the IP address is a valid address.
        ipaddress.ip_address(host)

        # Get information from Beolink self method.
        client = MozartClient(host)

        beolink_self = client.get_beolink_self(async_req=True, _request_timeout=3).get()

        beolink_jid = beolink_self.jid
        name = beolink_self.friendly_name
        serial_number = beolink_self.jid.split(".")[2].split("@")[0]

        return (beolink_jid, name, serial_number)

    except ApiException as error:
        raise AbortFlow(reason=API_EXCEPTION) from error

    except NewConnectionError as error:
        raise AbortFlow(reason=NEW_CONNECTION_ERROR) from error

    except MaxRetryError as error:
        raise AbortFlow(reason=MAX_RETRY_ERROR) from error

    except ValueError as error:
        raise AbortFlow(reason=VALUE_ERROR) from error


class UserInput(TypedDict):
    """TypedDict for user_input."""

    name: str
    friendly_name: str
    volume_step: int
    default_volume: int
    max_volume: int
    host: str
    model: str
    jid: str


class BangOlufsenConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    def __init__(self) -> None:
        """Init the config flow."""
        self._host: str = ""
        self._name: str = ""
        self._model: str = ""
        self._serial_number: str = ""
        self._beolink_jid: str = ""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._model = user_input[CONF_MODEL]
            self._beolink_jid, self._name, self._serial_number = await _validate_host(
                self._host
            )

            await self.async_set_unique_id(self._serial_number)
            self._abort_if_unique_id_configured()

            return await self.async_step_confirm()

        data_schema = {
            vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
            vol.Required(CONF_MODEL, default=DEFAULT_MODEL): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=COMPATIBLE_MODELS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(data_schema),
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle discovery using Zeroconf."""
        self._host = discovery_info.host
        self._model = discovery_info.hostname[:-16].replace("-", " ")
        self._serial_number = discovery_info.properties[ATTR_SERIAL_NUMBER]
        self._beolink_jid = f"{discovery_info.properties[ATTR_TYPE_NUMBER]}.{discovery_info.properties[ATTR_ITEM_NUMBER]}.{self._serial_number}@products.bang-olufsen.com"
        self._name = discovery_info.properties[ATTR_FRIENDLY_NAME]

        self.context["title_placeholders"] = {"name": self._name}

        await self.async_set_unique_id(self._serial_number)
        self._abort_if_unique_id_configured()

        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: UserInput | None = None
    ) -> FlowResult:
        """Confirm the configuration of the device."""
        if user_input is not None:
            # Get the desired friendly name before changing it for generating entity_id
            self._name = user_input[CONF_NAME]

            # Make sure that all information is included
            data = user_input
            data[CONF_HOST] = self._host
            data[CONF_MODEL] = self._model
            data[CONF_BEOLINK_JID] = self._beolink_jid
            data[CONF_FRIENDLY_NAME] = self._name

            # Manually define the entity_id
            model_name = underscore(self._model.replace(" ", "_"))
            data[CONF_NAME] = f"{model_name}_{self._serial_number}"

            return self.async_create_entry(
                title=self._name,
                data=data,
            )

        client = MozartClient(self._host)
        volume_settings = client.get_volume_settings(async_req=True).get()

        data_schema = _config_schema(
            name=self._name,
            default_volume=volume_settings.default.level,
            max_volume=volume_settings.maximum.level,
        )

        self._set_confirm_only()

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema(data_schema),
            description_placeholders={
                CONF_HOST: self._host,
                CONF_MODEL: self._model,
                CONF_SERIAL_NUMBER: self._serial_number,
            },
            last_step=True,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow handler."""
        return BangOlufsenOptionsFlowHandler(config_entry)


class BangOlufsenOptionsFlowHandler(OptionsFlow):
    """Handle an options flow."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the options flow handler."""
        self._config_entry: ConfigEntry = config_entry

    async def async_step_init(self, user_input: UserInput | None = None) -> FlowResult:
        """Manage the options menu."""
        if user_input is not None:
            # Make sure that everything get included in the data.
            data = user_input

            data[CONF_MODEL] = self._config_entry.data[CONF_MODEL]
            data[CONF_BEOLINK_JID] = self._config_entry.data[CONF_BEOLINK_JID]
            data[CONF_FRIENDLY_NAME] = user_input[CONF_NAME]
            if not self.show_advanced_options:
                data[CONF_HOST] = self._config_entry.data[CONF_HOST]

            # Check connection
            await _validate_host(data[CONF_HOST])
            return self.async_create_entry(title=data[CONF_NAME], data=data)

        # Create data schema with the last configuration as default values.
        data_schema = _config_schema(
            name=self._config_entry.data[CONF_FRIENDLY_NAME],
            volume_step=self._config_entry.data[CONF_VOLUME_STEP],
            default_volume=self._config_entry.data[CONF_DEFAULT_VOLUME],
            max_volume=self._config_entry.data[CONF_MAX_VOLUME],
        )

        # Only show the ip address if advanced options are on.
        if self.show_advanced_options:
            data_schema.update(
                {
                    vol.Required(
                        CONF_HOST, default=self._config_entry.data[CONF_HOST]
                    ): cv.string
                },
            )

        # Create options form with selected options.
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(data_schema),
            last_step=True,
        )
