"""Config flow for the Bang & Olufsen integration."""

from __future__ import annotations

from ipaddress import AddressValueError, IPv4Address
from typing import Any, TypedDict

from aiohttp.client_exceptions import ClientConnectorError
from mozart_api.exceptions import ApiException
from mozart_api.mozart_client import MozartClient
import voluptuous as vol

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN
from homeassistant.components.input_button import DOMAIN as INPUT_BUTTON_DOMAIN
from homeassistant.components.input_number import DOMAIN as INPUT_NUMBER_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
from homeassistant.components.scene import DOMAIN as SCENE_DOMAIN
from homeassistant.components.script import DOMAIN as SCRIPT_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import (
    ATTR_NAME,
    CONF_ENTITIES,
    CONF_HOST,
    CONF_ICON,
    CONF_MODEL,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
)
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from homeassistant.util.ssl import get_default_context
from homeassistant.util.uuid import random_uuid_hex

from .beoremote_halo.helpers import (
    clear_default_button,
    delete_page,
    get_all_buttons,
    get_default_button,
    get_page_from_id,
    get_page_index,
    set_default_button,
    update_button,
    update_page,
)
from .beoremote_halo.models import (
    BaseConfiguration,
    Button,
    Configuration,
    Icon,
    Icons,
    Page,
    Text,
)
from .const import (
    ATTR_FRIENDLY_NAME,
    ATTR_HALO_SERIAL_NUMBER,
    ATTR_ITEM_NUMBER,
    ATTR_MOZART_SERIAL_NUMBER,
    ATTR_TYPE_NUMBER,
    CONF_DEFAULT_BUTTON,
    CONF_ENTITY_MAP,
    CONF_HALO,
    CONF_PAGE_TITLE,
    CONF_PAGES,
    CONF_SERIAL_NUMBER,
    CONF_SUBTITLE,
    CONF_TEXT,
    CONF_TITLE,
    DEFAULT_MODEL,
    DOMAIN,
    HALO_BUTTON_ICONS,
    HALO_MAX_NUM_BUTTONS,
    HALO_MAX_NUM_PAGES,
    HALO_TEXT_LENGTH,
    HALO_TITLE_LENGTH,
    MOZART_MODELS,
    ZEROCONF_HALO,
    ZEROCONF_MOZART,
    BangOlufsenModel,
)
from .util import get_serial_number_from_jid


class BangOlufsenEntryData(TypedDict, total=False):
    """TypedDict for config_entry data."""

    host: str
    model: str
    name: str
    # Mozart
    jid: str
    # Halo
    # Does not seem to handle objects well through restarts
    halo: dict | None
    entity_map: dict[str, str]


# Map exception types to strings
_exception_map = {
    ApiException: "api_exception",
    ClientConnectorError: "client_connector_error",
    TimeoutError: "timeout_error",
    AddressValueError: "invalid_ip",
}


class BangOlufsenConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    _beolink_jid = ""
    _mozart_client: MozartClient
    _host = ""
    _model = ""
    _name = ""
    _serial_number = ""

    def __init__(self) -> None:
        """Init the config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_MODEL, default=DEFAULT_MODEL): SelectSelector(
                    SelectSelectorConfig(options=MOZART_MODELS)
                ),
            }
        )

        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._model = user_input[CONF_MODEL]

            try:
                IPv4Address(self._host)
            except AddressValueError as error:
                return self.async_show_form(
                    step_id="user",
                    data_schema=data_schema,
                    errors={"base": _exception_map[type(error)]},
                )

            self._mozart_client = MozartClient(
                self._host, ssl_context=get_default_context()
            )

            # Try to get information from Beolink self method.
            async with self._mozart_client:
                try:
                    beolink_self = await self._mozart_client.get_beolink_self(
                        _request_timeout=3
                    )
                except (
                    ApiException,
                    ClientConnectorError,
                    TimeoutError,
                ) as error:
                    return self.async_show_form(
                        step_id="user",
                        data_schema=data_schema,
                        errors={"base": _exception_map[type(error)]},
                    )

            self._beolink_jid = beolink_self.jid
            self._serial_number = get_serial_number_from_jid(beolink_self.jid)

            await self.async_set_unique_id(self._serial_number)
            self._abort_if_unique_id_configured()

            return await self._create_entry()

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle discovery using Zeroconf."""

        # Ensure that an IPv4 address is received
        self._host = discovery_info.host

        try:
            IPv4Address(self._host)
        except AddressValueError:
            return self.async_abort(reason="ipv6_address")

        # Default to Mozart products
        name_key = ATTR_FRIENDLY_NAME

        # Handle Mozart based products
        if discovery_info.type == ZEROCONF_MOZART:
            if (status := await self._zeroconf_mozart(discovery_info)) is not None:
                return status

        # Handle Beoremote Halo
        elif discovery_info.type == ZEROCONF_HALO:
            self._zeroconf_halo(discovery_info)
            name_key = ATTR_NAME

        await self.async_set_unique_id(self._serial_number)
        self._abort_if_unique_id_configured(updates={CONF_HOST: self._host})

        # Set the discovered device title
        self.context["title_placeholders"] = {
            "name": discovery_info.properties[name_key]
        }

        return await self.async_step_zeroconf_confirm()

    def _zeroconf_halo(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult | None:
        """Handle Zeroconf discovery of Halo."""
        self._serial_number = discovery_info.properties[ATTR_HALO_SERIAL_NUMBER]
        self._model = BangOlufsenModel.BEOREMOTE_HALO
        return None

    async def _zeroconf_mozart(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult | None:
        """Handle Zeroconf discovery of Mozart products."""
        # Check if the discovered device is a Mozart device
        if ATTR_FRIENDLY_NAME not in discovery_info.properties:
            return self.async_abort(reason="not_mozart_device")

        # Check connection to ensure valid address is received
        self._mozart_client = MozartClient(
            self._host, ssl_context=get_default_context()
        )

        async with self._mozart_client:
            try:
                await self._mozart_client.get_beolink_self(_request_timeout=3)
            except (ClientConnectorError, TimeoutError):
                return self.async_abort(reason="invalid_address")

        self._model = discovery_info.hostname[:-16].replace("-", " ")
        self._serial_number = discovery_info.properties[ATTR_MOZART_SERIAL_NUMBER]
        self._beolink_jid = f"{discovery_info.properties[ATTR_TYPE_NUMBER]}.{discovery_info.properties[ATTR_ITEM_NUMBER]}.{self._serial_number}@products.bang-olufsen.com"

        return None

    async def _create_entry(self) -> ConfigFlowResult:
        """Create the config entry for a discovered or manually configured Bang & Olufsen device."""
        # Ensure that created entities have a unique and easily identifiable id and not a "friendly name"
        self._name = f"{self._model}-{self._serial_number}"

        return self.async_create_entry(
            title=self._name,
            data=BangOlufsenEntryData(
                host=self._host,
                jid=self._beolink_jid,
                model=self._model,
                name=self._name,
                halo=None,
            ),
        )

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm the configuration of the device."""
        if user_input is not None:
            return await self._create_entry()

        self._set_confirm_only()

        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={
                CONF_HOST: self._host,
                CONF_MODEL: self._model,
                CONF_SERIAL_NUMBER: self._serial_number,
            },
            last_step=True,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Create the options flow."""
        # This option should only be available for the Halo,
        # but this is currently not supported by Home Assistant.
        return HaloOptionsFlowHandler()


class HaloOptionsFlowHandler(OptionsFlow):
    """HaloOptionsFlowHandler."""

    def __init__(self) -> None:
        """Initialize options."""
        self._configuration: BaseConfiguration = BaseConfiguration(Configuration([]))
        self._entity_ids: list[str] = []
        self._entity_map: dict[str, str] = {}
        self._page: Page
        self._default_button: Button | None
        self._page_being_modified = False
        # Only used when modifying / adding / removing buttons
        self._button: Button | None = None
        self._entity_ids_in_page: list[str] = []

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        # Reject options for any non-Halo device
        if self.config_entry.data[CONF_MODEL] != BangOlufsenModel.BEOREMOTE_HALO:
            return self.async_abort(
                reason="invalid_model",
                description_placeholders={"model": self.config_entry.data[CONF_MODEL]},
            )

        # Load stored configuration, entity map and current default button
        if self.config_entry.options:
            self._configuration = BaseConfiguration.from_dict(
                self.config_entry.options[CONF_HALO]
            )
            self._entity_map = self.config_entry.options[CONF_ENTITY_MAP]

        # Check for a current default button.
        self._default_button = get_default_button(self._configuration)

        options = []
        # Remove "page" option if 3 already are in the configuration
        if len(self._configuration.configuration.pages) < HALO_MAX_NUM_PAGES:
            options.append("page")

        # Add options that require at least one page in the configuration
        if len(self._configuration.configuration.pages) > 0:
            options.extend(["modify_page", "delete_pages", "modify_default"])

        return self.async_show_menu(step_id="init", menu_options=options)

    async def async_step_page(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a new page."""

        if user_input is not None:
            self._entity_ids = user_input[CONF_ENTITIES]

            # Don't create a new page if an existing page is being modified
            if not self._page_being_modified:
                self._page = Page(user_input[CONF_PAGE_TITLE], [], id=self._halo_uuid())
            else:
                new_buttons = self._page.buttons

                # Remove any deleted buttons
                entity_ids_to_remove = [
                    entity_id
                    for entity_id in self._entity_ids_in_page
                    if entity_id not in self._entity_ids
                ]

                # Get button ID and remove from page and entity_map
                for entity_id in entity_ids_to_remove:
                    for button in self._page.buttons:
                        if self._entity_map[button.id] == entity_id:
                            self._entity_map.pop(button.id)
                            new_buttons.remove(button)

                # Add the (modified?) page title and buttons to the current configuration
                self._configuration = update_page(
                    self._configuration,
                    self._page.id,
                    user_input[CONF_PAGE_TITLE],
                    new_buttons,
                )

            return await self.async_step_button()

        return self.async_show_form(step_id="page", data_schema=self._page_schema())

    async def async_step_button(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add buttons to new page."""
        if user_input is not None:
            # Create a new button when adding a new page or adding a button to an existing page
            if not self._page_being_modified or self._button is None:
                button = Button(
                    title=user_input[CONF_TITLE],
                    subtitle=user_input[CONF_SUBTITLE],
                    content=(
                        Icon(Icons[user_input[CONF_ICON]])
                        if CONF_ICON in user_input
                        else Text(user_input[CONF_TEXT])
                    ),
                    id=self._halo_uuid(),
                )

                # Update entity_map
                self._entity_map[button.id] = self._entity_ids[-1]

                # Add to current page
                self._page.buttons.append(button)
            else:
                # Update existing button
                self._configuration = update_button(
                    self._configuration,
                    self._button.id,
                    title=user_input[CONF_TITLE],
                    subtitle=user_input[CONF_SUBTITLE],
                    content=(
                        Icon(Icons[user_input[CONF_ICON]])
                        if CONF_ICON in user_input
                        else Text(user_input[CONF_TEXT])
                    ),
                )

            self._entity_ids.pop()

            if not self._entity_ids:
                # Add newly created page to configuration
                if not self._page_being_modified:
                    self._configuration.configuration.pages.append(self._page)

                return self.async_create_entry(
                    title=f"Page {self._page.title} added to configuration",
                    data=BangOlufsenEntryData(
                        host=self.config_entry.data[CONF_HOST],
                        model=self.config_entry.data[CONF_MODEL],
                        name=self.config_entry.title,
                        halo=self._configuration.to_dict(),
                        entity_map=self._entity_map,
                    ),
                )

        if not self._page_being_modified:
            button_schema = self._button_schema()
        # Add current values as "default" values if page is being modified
        else:
            # Get current button attributes from entity_map and page
            for button in self._page.buttons:
                if self._entity_map[button.id] == self._entity_ids[-1]:
                    self._button = button
            # Newly added buttons won't be available in the entity_map and won't have any initial values
            if self._button is None:
                button_schema = self._button_schema()
            else:
                button_schema = self._button_schema(
                    self._button.title, self._button.subtitle, self._button.content
                )

        return self.async_show_form(
            step_id="button",
            data_schema=button_schema,
            description_placeholders={
                "entity": self._entity_ids[-1],
                "page": self._page.title,
            },
        )

    async def async_step_modify_page(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Modify a page."""

        if user_input is not None:
            page_id = self._get_uuid_from_string(user_input[CONF_PAGES])

            # Get buttons from page
            self._page = get_page_from_id(self._configuration, page_id)
            self._page_being_modified = True
            self._entity_ids_in_page = [
                self._entity_map[button.id] for button in self._page.buttons
            ]

            return self.async_show_form(
                step_id="page",
                data_schema=self._page_schema(
                    page_title=self._page.title,
                    entities=self._entity_ids_in_page,
                ),
            )

        return self.async_show_form(
            step_id="modify_page",
            data_schema=self._page_selector_schema(multiple=False),
        )

    async def async_step_delete_pages(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Delete selected pages."""

        if user_input is not None:
            for page_title in user_input[CONF_PAGES]:
                page_id = self._get_uuid_from_string(page_title)

                # Remove used button ids from entity_map
                for button in self._configuration.configuration.pages[
                    get_page_index(self._configuration, page_id)
                ].buttons:
                    self._entity_map.pop(button.id)

                # Delete page from configuration
                self._configuration = delete_page(self._configuration, page_id)

            return self.async_create_entry(
                title="Updated configuration",
                data=BangOlufsenEntryData(
                    host=self.config_entry.data[CONF_HOST],
                    model=self.config_entry.data[CONF_MODEL],
                    name=self.config_entry.title,
                    halo=self._configuration.to_dict(),
                    entity_map=self._entity_map,
                ),
            )
        return self.async_show_form(
            step_id="delete_pages",
            data_schema=self._page_selector_schema(multiple=True),
        )

    async def async_step_modify_default(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Enter default options."""

        options = []
        description_placeholders = {}

        # Add remove_default as an option if a default button has been set
        if self._default_button is not None:
            options.append("remove_default")
            description_placeholders["button"] = self._default_button.title
            # Check if there are any buttons available to select as default (at least 1 that is not default)
            if len(get_all_buttons(self._configuration)) > 1:
                options.append("select_default")
        else:
            options.append("select_default")

        return self.async_show_menu(
            step_id="modify_default",
            menu_options=options,
            description_placeholders=description_placeholders,
        )

    async def async_step_select_default(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select a default button."""
        if user_input is not None:
            # Remove any previous default button
            self._configuration = clear_default_button(self._configuration)

            # Update configuration with new default
            set_default_button(
                self._configuration,
                self._get_uuid_from_string(user_input[CONF_DEFAULT_BUTTON]),
                True,
            )

            return self.async_create_entry(
                title="Updated configuration",
                data=BangOlufsenEntryData(
                    host=self.config_entry.data[CONF_HOST],
                    model=self.config_entry.data[CONF_MODEL],
                    name=self.config_entry.title,
                    halo=self._configuration.to_dict(),
                    entity_map=self._entity_map,
                ),
            )

        # Get all buttons and check for a current default button
        buttons = []
        for page in self._configuration.configuration.pages:
            buttons.extend(
                [
                    f"{page.title}-{button.title} ({button.id})"
                    for button in page.buttons
                    if button.default is False
                ]
            )

        return self.async_show_form(
            step_id="select_default",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEFAULT_BUTTON): SelectSelector(
                        SelectSelectorConfig(
                            options=buttons,
                            sort=True,
                        )
                    ),
                }
            ),
        )

    async def async_step_remove_default(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Remove the default attribute from a button."""

        # Remove current default from configuration
        self._configuration = clear_default_button(self._configuration)

        return self.async_create_entry(
            title="Updated configuration",
            data=BangOlufsenEntryData(
                host=self.config_entry.data[CONF_HOST],
                model=self.config_entry.data[CONF_MODEL],
                name=self.config_entry.title,
                halo=self._configuration.to_dict(),
                entity_map=self._entity_map,
            ),
        )

    def _halo_uuid(self) -> str:
        """Get a properly formatted Halo UUID."""
        # UUIDs from uuid1() are not unique when generated in Home Assistant (???)
        # Use this function to generate and format UUIDs instead.
        temp_uuid = random_uuid_hex()
        return f"{temp_uuid[:8]}-{temp_uuid[8:12]}-{temp_uuid[12:16]}-{temp_uuid[16:20]}-{temp_uuid[20:32]}"

    def _get_uuid_from_string(self, string: str) -> str:
        """Get Halo UUID from formatted string: * (<UUID>)."""
        return string[-37:-1]

    def _page_schema(
        self,
        page_title: str | vol.Undefined = vol.UNDEFINED,
        entities: list[str] | vol.Undefined = vol.UNDEFINED,
    ) -> vol.Schema:
        """Fill schema for page modification or creation."""

        return vol.Schema(
            {
                vol.Required(CONF_PAGE_TITLE, default=page_title): str,
                vol.Required(CONF_ENTITIES, default=entities): vol.All(
                    vol.Length(min=1, max=HALO_MAX_NUM_BUTTONS),
                    EntitySelector(
                        EntitySelectorConfig(
                            multiple=True,
                            domain=[
                                BINARY_SENSOR_DOMAIN,
                                BUTTON_DOMAIN,
                                INPUT_BOOLEAN_DOMAIN,
                                INPUT_BUTTON_DOMAIN,
                                INPUT_NUMBER_DOMAIN,
                                LIGHT_DOMAIN,
                                NUMBER_DOMAIN,
                                SCENE_DOMAIN,
                                SCRIPT_DOMAIN,
                                SENSOR_DOMAIN,
                                SWITCH_DOMAIN,
                            ],
                        )
                    ),
                ),
            }
        )

    def _button_schema(
        self,
        title: str | vol.Undefined = vol.UNDEFINED,
        subtitle: str = "",
        content: Icon | Text | None = None,
    ) -> vol.Schema:
        """Fill schema for button modification or creation."""

        class ExclusiveKwargs(TypedDict, total=False):
            schema: vol.Schemable
            group_of_exclusion: str
            msg: str | None
            description: str | Any

        icon_kwargs: ExclusiveKwargs = {
            "schema": CONF_ICON,
            "group_of_exclusion": "content",
            "msg": "Choose either an Icon or Text",
        }
        text_kwargs: ExclusiveKwargs = {
            "schema": CONF_TEXT,
            "group_of_exclusion": "content",
            "msg": "Choose either an Icon or Text",
        }
        # Add suggested value to kwargs if an Icon or Text value is available
        if isinstance(content, Icon):
            icon_kwargs["description"] = {"suggested_value": content.icon.name}
        elif isinstance(content, Text):
            text_kwargs["description"] = {"suggested_value": content.text}

        return vol.Schema(
            {
                vol.Required(CONF_TITLE, default=title): vol.All(
                    str,
                    vol.Length(max=HALO_TITLE_LENGTH),
                ),
                vol.Optional(CONF_SUBTITLE, default=subtitle): vol.All(
                    str,
                    vol.Length(max=HALO_TITLE_LENGTH),
                ),
                vol.Exclusive(**icon_kwargs): SelectSelector(
                    SelectSelectorConfig(options=HALO_BUTTON_ICONS)
                ),
                vol.Exclusive(**text_kwargs): vol.All(
                    str,
                    vol.Length(max=HALO_TEXT_LENGTH),
                ),
            },
        )

    def _page_selector_schema(self, multiple: bool) -> vol.Schema:
        """Select a single or multiple pages from title."""

        return vol.Schema(
            {
                vol.Required(CONF_PAGES): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            f"{page.title} - ({page.id})"
                            for page in self._configuration.configuration.pages
                        ],
                        multiple=multiple,
                    )
                )
            }
        )
