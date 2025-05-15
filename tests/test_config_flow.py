"""Test the bang_olufsen config_flow."""

from copy import deepcopy
from unittest.mock import AsyncMock, Mock

from aiohttp.client_exceptions import ClientConnectorError
from mozart_api.exceptions import ApiException
import pytest

from homeassistant.components.bang_olufsen.const import (
    DOMAIN,
    HALO_OPTION_DELETE_PAGES,
    HALO_OPTION_MODIFY_DEFAULT,
    HALO_OPTION_MODIFY_PAGE,
    HALO_OPTION_PAGE,
    HALO_OPTION_REMOVE_DEFAULT,
    HALO_OPTION_SELECT_DEFAULT,
)
from homeassistant.config_entries import SOURCE_USER, SOURCE_ZEROCONF
from homeassistant.const import CONF_SOURCE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .const import (
    TEST_DATA_CREATE_ENTRY,
    TEST_DATA_USER,
    TEST_DATA_USER_INVALID,
    TEST_DATA_ZEROCONF,
    TEST_DATA_ZEROCONF_IPV6,
    TEST_DATA_ZEROCONF_NOT_MOZART,
    TEST_HALO_BUTTON_2_ID,
    TEST_HALO_DATA_BUTTON,
    TEST_HALO_DATA_BUTTON_2,
    TEST_HALO_DATA_BUTTON_2_MODIFIED,
    TEST_HALO_DATA_BUTTON_MODIFIED,
    TEST_HALO_DATA_CREATE_ENTRY,
    TEST_HALO_DATA_CREATE_ENTRY_WITH_CONFIGURATION,
    TEST_HALO_DATA_CREATE_ENTRY_WITH_CONFIGURATION_2_BUTTONS,
    TEST_HALO_DATA_CREATE_ENTRY_WITH_CONFIGURATION_2_BUTTONS_MODIFIED,
    TEST_HALO_DATA_CREATE_ENTRY_WITH_CONFIGURATION_DEFAULT,
    TEST_HALO_DATA_CREATE_ENTRY_WITH_CONFIGURATION_EMPTY,
    TEST_HALO_DATA_PAGE,
    TEST_HALO_DATA_PAGE_2_BUTTONS,
    TEST_HALO_DATA_SELECT_DEFAULT,
    TEST_HALO_DATA_SELECT_PAGE,
    TEST_HALO_DATA_SELECT_PAGES,
    TEST_HALO_DATA_ZEROCONF,
    TEST_HALO_NAME,
    TEST_HALO_PAGE,
    TEST_HALO_SERIAL,
    TEST_HALO_UUID_TARGET,
)

from tests.common import MockConfigEntry, patch

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


# General / Mozart tests


async def test_config_flow_timeout_error(
    hass: HomeAssistant, mock_mozart_client: AsyncMock
) -> None:
    """Test we handle timeout_error."""
    mock_mozart_client.get_beolink_self.side_effect = TimeoutError()

    result_user = await hass.config_entries.flow.async_init(
        handler=DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
        data=TEST_DATA_USER,
    )
    assert result_user["type"] is FlowResultType.FORM
    assert result_user["errors"] == {"base": "timeout_error"}

    assert mock_mozart_client.get_beolink_self.call_count == 1


async def test_config_flow_client_connector_error(
    hass: HomeAssistant, mock_mozart_client: AsyncMock
) -> None:
    """Test we handle client_connector_error."""
    mock_mozart_client.get_beolink_self.side_effect = ClientConnectorError(
        Mock(), Mock()
    )

    result_user = await hass.config_entries.flow.async_init(
        handler=DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
        data=TEST_DATA_USER,
    )
    assert result_user["type"] is FlowResultType.FORM
    assert result_user["errors"] == {"base": "client_connector_error"}

    assert mock_mozart_client.get_beolink_self.call_count == 1


async def test_config_flow_invalid_ip(hass: HomeAssistant) -> None:
    """Test we handle invalid_ip."""

    result_user = await hass.config_entries.flow.async_init(
        handler=DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
        data=TEST_DATA_USER_INVALID,
    )
    assert result_user["type"] is FlowResultType.FORM
    assert result_user["errors"] == {"base": "invalid_ip"}


async def test_config_flow_api_exception(
    hass: HomeAssistant, mock_mozart_client: AsyncMock
) -> None:
    """Test we handle api_exception."""
    mock_mozart_client.get_beolink_self.side_effect = ApiException()

    result_user = await hass.config_entries.flow.async_init(
        handler=DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
        data=TEST_DATA_USER,
    )
    assert result_user["type"] is FlowResultType.FORM
    assert result_user["errors"] == {"base": "api_exception"}

    assert mock_mozart_client.get_beolink_self.call_count == 1


async def test_config_flow(hass: HomeAssistant, mock_mozart_client: AsyncMock) -> None:
    """Test config flow."""

    result_init = await hass.config_entries.flow.async_init(
        handler=DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
        data=None,
    )

    assert result_init["type"] is FlowResultType.FORM
    assert result_init["step_id"] == "user"

    result_user = await hass.config_entries.flow.async_configure(
        flow_id=result_init["flow_id"],
        user_input=TEST_DATA_USER,
    )

    assert result_user["type"] is FlowResultType.CREATE_ENTRY
    assert result_user["data"] == TEST_DATA_CREATE_ENTRY

    assert mock_mozart_client.get_beolink_self.call_count == 1


async def test_config_flow_zeroconf(
    hass: HomeAssistant, mock_mozart_client: AsyncMock
) -> None:
    """Test zeroconf discovery."""

    result_zeroconf = await hass.config_entries.flow.async_init(
        handler=DOMAIN,
        context={CONF_SOURCE: SOURCE_ZEROCONF},
        data=TEST_DATA_ZEROCONF,
    )

    assert result_zeroconf["type"] is FlowResultType.FORM
    assert result_zeroconf["step_id"] == "zeroconf_confirm"

    result_confirm = await hass.config_entries.flow.async_configure(
        flow_id=result_zeroconf["flow_id"], user_input={}
    )

    assert result_confirm["type"] is FlowResultType.CREATE_ENTRY
    assert result_confirm["data"] == TEST_DATA_CREATE_ENTRY

    assert mock_mozart_client.get_beolink_self.call_count == 1


async def test_config_flow_zeroconf_not_mozart_device(hass: HomeAssistant) -> None:
    """Test zeroconf discovery of invalid device."""

    result_user = await hass.config_entries.flow.async_init(
        handler=DOMAIN,
        context={CONF_SOURCE: SOURCE_ZEROCONF},
        data=TEST_DATA_ZEROCONF_NOT_MOZART,
    )

    assert result_user["type"] is FlowResultType.ABORT
    assert result_user["reason"] == "not_mozart_device"


async def test_config_flow_zeroconf_ipv6(hass: HomeAssistant) -> None:
    """Test zeroconf discovery with IPv6 IP address."""

    result_user = await hass.config_entries.flow.async_init(
        handler=DOMAIN,
        context={CONF_SOURCE: SOURCE_ZEROCONF},
        data=TEST_DATA_ZEROCONF_IPV6,
    )

    assert result_user["type"] is FlowResultType.ABORT
    assert result_user["reason"] == "ipv6_address"


async def test_config_flow_zeroconf_invalid_ip(
    hass: HomeAssistant, mock_mozart_client: AsyncMock
) -> None:
    """Test zeroconf discovery with invalid IP address."""
    mock_mozart_client.get_beolink_self.side_effect = ClientConnectorError(
        Mock(), Mock()
    )

    result_user = await hass.config_entries.flow.async_init(
        handler=DOMAIN,
        context={CONF_SOURCE: SOURCE_ZEROCONF},
        data=TEST_DATA_ZEROCONF,
    )

    assert result_user["type"] is FlowResultType.ABORT
    assert result_user["reason"] == "invalid_address"


async def test_config_flow_options_mozart(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test Mozart options."""
    # Setup entry
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result_options = await hass.config_entries.options.async_init(
        mock_config_entry.entry_id
    )

    assert result_options["type"] is FlowResultType.ABORT
    assert result_options["reason"] == "invalid_model"


# Halo related tests


async def test_halo_config_flow_zeroconf(hass: HomeAssistant) -> None:
    """Test Halo zeroconf discovery."""

    result_zeroconf = await hass.config_entries.flow.async_init(
        handler=DOMAIN,
        context={CONF_SOURCE: SOURCE_ZEROCONF},
        data=TEST_HALO_DATA_ZEROCONF,
    )

    assert result_zeroconf["type"] is FlowResultType.FORM
    assert result_zeroconf["step_id"] == "zeroconf_confirm"

    result_confirm = await hass.config_entries.flow.async_configure(
        flow_id=result_zeroconf["flow_id"], user_input={}
    )

    assert result_confirm["type"] is FlowResultType.CREATE_ENTRY
    assert result_confirm["data"] == TEST_HALO_DATA_CREATE_ENTRY


async def test_halo_config_flow_options_add_page(
    hass: HomeAssistant, mock_halo_uuid: AsyncMock
) -> None:
    """Test Halo options by adding a page with one button."""
    # Setup Halo
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEST_HALO_SERIAL,
        data=TEST_HALO_DATA_CREATE_ENTRY,
        title=TEST_HALO_NAME,
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Start options
    result_init = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result_init["type"] is FlowResultType.MENU
    assert result_init["step_id"] == "init"
    # Ensure only the expected options are available
    assert result_init["menu_options"] == [HALO_OPTION_PAGE]

    # Select "Create a new page"
    result_options = await hass.config_entries.options.async_configure(
        flow_id=result_init["flow_id"],
        user_input={"next_step_id": HALO_OPTION_PAGE},
    )
    assert result_options["type"] is FlowResultType.FORM
    assert result_options["step_id"] == HALO_OPTION_PAGE

    # Configure page
    result_page = await hass.config_entries.options.async_configure(
        flow_id=result_options["flow_id"],
        user_input=TEST_HALO_DATA_PAGE,
    )
    assert result_page["type"] is FlowResultType.FORM
    assert result_page["step_id"] == "button"

    # Configure button
    result_button = await hass.config_entries.options.async_configure(
        flow_id=result_page["flow_id"],
        user_input=TEST_HALO_DATA_BUTTON,
    )
    assert result_button["type"] is FlowResultType.CREATE_ENTRY
    assert result_button["data"] == TEST_HALO_DATA_CREATE_ENTRY_WITH_CONFIGURATION


async def test_halo_config_flow_options_delete_page(
    hass: HomeAssistant, integration_halo: None, mock_config_entry_halo: MockConfigEntry
) -> None:
    """Test Halo options by deleting an existing page."""

    # Start options
    result_init = await hass.config_entries.options.async_init(
        mock_config_entry_halo.entry_id
    )
    assert result_init["type"] is FlowResultType.MENU
    assert result_init["step_id"] == "init"
    # Ensure only the expected options are available
    assert result_init["menu_options"] == [
        HALO_OPTION_PAGE,
        HALO_OPTION_MODIFY_PAGE,
        HALO_OPTION_DELETE_PAGES,
        HALO_OPTION_MODIFY_DEFAULT,
    ]

    # Select "Delete existing pages"
    result_options = await hass.config_entries.options.async_configure(
        flow_id=result_init["flow_id"],
        user_input={"next_step_id": HALO_OPTION_DELETE_PAGES},
    )
    assert result_options["type"] is FlowResultType.FORM
    assert result_options["step_id"] == HALO_OPTION_DELETE_PAGES

    # Select page
    result_page = await hass.config_entries.options.async_configure(
        flow_id=result_options["flow_id"],
        user_input=TEST_HALO_DATA_SELECT_PAGES,
    )
    assert result_page["type"] is FlowResultType.CREATE_ENTRY
    assert result_page["data"] == TEST_HALO_DATA_CREATE_ENTRY_WITH_CONFIGURATION_EMPTY


async def test_halo_config_flow_options_modify_buttons(hass: HomeAssistant) -> None:
    """Test Halo options by modifying the title, subtitle, Icon->Text and Text->state for content for 2 buttons in an existing page."""
    # Setup Halo with 2 buttons to test default values for both Icon and Text content
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEST_HALO_SERIAL,
        data=TEST_HALO_DATA_CREATE_ENTRY,
        options=deepcopy(TEST_HALO_DATA_CREATE_ENTRY_WITH_CONFIGURATION_2_BUTTONS),
        title=TEST_HALO_NAME,
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Start options
    result_init = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result_init["type"] is FlowResultType.MENU
    assert result_init["step_id"] == "init"
    # Ensure only the expected options are available
    assert result_init["menu_options"] == [
        HALO_OPTION_PAGE,
        HALO_OPTION_MODIFY_PAGE,
        HALO_OPTION_DELETE_PAGES,
        HALO_OPTION_MODIFY_DEFAULT,
    ]

    # Select "Modify an existing page"
    result_options = await hass.config_entries.options.async_configure(
        flow_id=result_init["flow_id"],
        user_input={"next_step_id": HALO_OPTION_MODIFY_PAGE},
    )
    assert result_options["type"] is FlowResultType.FORM
    assert result_options["step_id"] == HALO_OPTION_MODIFY_PAGE

    # Select page
    result_page = await hass.config_entries.options.async_configure(
        flow_id=result_options["flow_id"],
        user_input=TEST_HALO_DATA_SELECT_PAGE,
    )
    assert result_page["type"] is FlowResultType.FORM
    assert result_page["step_id"] == HALO_OPTION_PAGE

    # Proceed without changing default values
    result_modify_page = await hass.config_entries.options.async_configure(
        flow_id=result_page["flow_id"],
        user_input=TEST_HALO_DATA_PAGE_2_BUTTONS,
    )
    assert result_modify_page["type"] is FlowResultType.FORM
    assert result_modify_page["step_id"] == "button"

    # Configure and modify button
    result_button = await hass.config_entries.options.async_configure(
        flow_id=result_modify_page["flow_id"],
        user_input=TEST_HALO_DATA_BUTTON_MODIFIED,
    )
    assert result_button["type"] is FlowResultType.FORM
    assert result_button["step_id"] == "button"

    # Configure and modify button 2
    result_button_2 = await hass.config_entries.options.async_configure(
        flow_id=result_button["flow_id"],
        user_input=TEST_HALO_DATA_BUTTON_2_MODIFIED,
    )
    assert result_button_2["type"] is FlowResultType.CREATE_ENTRY
    assert (
        result_button_2["data"]
        == TEST_HALO_DATA_CREATE_ENTRY_WITH_CONFIGURATION_2_BUTTONS_MODIFIED
    )


async def test_halo_config_flow_options_modify_button(hass: HomeAssistant) -> None:
    """Test Halo options by modifying the content state->Text for a button in an existing page."""
    # Setup Halo with 2 buttons to test default values for state
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEST_HALO_SERIAL,
        data=TEST_HALO_DATA_CREATE_ENTRY,
        options=deepcopy(
            TEST_HALO_DATA_CREATE_ENTRY_WITH_CONFIGURATION_2_BUTTONS_MODIFIED
        ),
        title=TEST_HALO_NAME,
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Start options
    result_init = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result_init["type"] is FlowResultType.MENU
    assert result_init["step_id"] == "init"
    # Ensure only the expected options are available
    assert result_init["menu_options"] == [
        HALO_OPTION_PAGE,
        HALO_OPTION_MODIFY_PAGE,
        HALO_OPTION_DELETE_PAGES,
        HALO_OPTION_MODIFY_DEFAULT,
    ]

    # Select "Modify an existing page"
    result_options = await hass.config_entries.options.async_configure(
        flow_id=result_init["flow_id"],
        user_input={"next_step_id": HALO_OPTION_MODIFY_PAGE},
    )
    assert result_options["type"] is FlowResultType.FORM
    assert result_options["step_id"] == HALO_OPTION_MODIFY_PAGE

    # Select page
    result_page = await hass.config_entries.options.async_configure(
        flow_id=result_options["flow_id"],
        user_input=TEST_HALO_DATA_SELECT_PAGE,
    )
    assert result_page["type"] is FlowResultType.FORM
    assert result_page["step_id"] == HALO_OPTION_PAGE

    # Proceed without changing default values
    result_modify_page = await hass.config_entries.options.async_configure(
        flow_id=result_page["flow_id"],
        user_input=TEST_HALO_DATA_PAGE_2_BUTTONS,
    )
    assert result_modify_page["type"] is FlowResultType.FORM
    assert result_modify_page["step_id"] == "button"

    # Configure button and modify button
    result_button = await hass.config_entries.options.async_configure(
        flow_id=result_modify_page["flow_id"],
        user_input=TEST_HALO_DATA_BUTTON,
    )
    assert result_button["type"] is FlowResultType.FORM
    assert result_button["step_id"] == "button"

    # Configure and modify button 2
    result_button_2 = await hass.config_entries.options.async_configure(
        flow_id=result_button["flow_id"],
        user_input=TEST_HALO_DATA_BUTTON_2,
    )
    assert result_button_2["type"] is FlowResultType.CREATE_ENTRY
    assert (
        result_button_2["data"]
        == TEST_HALO_DATA_CREATE_ENTRY_WITH_CONFIGURATION_2_BUTTONS
    )


async def test_halo_config_flow_options_remove_button(hass: HomeAssistant) -> None:
    """Test Halo options by removing a button from a page."""
    # Setup Halo
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEST_HALO_SERIAL,
        data=TEST_HALO_DATA_CREATE_ENTRY,
        options=deepcopy(TEST_HALO_DATA_CREATE_ENTRY_WITH_CONFIGURATION_2_BUTTONS),
        title=TEST_HALO_NAME,
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Start options
    result_init = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result_init["type"] is FlowResultType.MENU
    assert result_init["step_id"] == "init"
    # Ensure only the expected options are available
    assert result_init["menu_options"] == [
        HALO_OPTION_PAGE,
        HALO_OPTION_MODIFY_PAGE,
        HALO_OPTION_DELETE_PAGES,
        HALO_OPTION_MODIFY_DEFAULT,
    ]

    # Select "Modify an existing page"
    result_options = await hass.config_entries.options.async_configure(
        flow_id=result_init["flow_id"],
        user_input={"next_step_id": HALO_OPTION_MODIFY_PAGE},
    )
    assert result_options["type"] is FlowResultType.FORM
    assert result_options["step_id"] == HALO_OPTION_MODIFY_PAGE

    # Select page
    result_page = await hass.config_entries.options.async_configure(
        flow_id=result_options["flow_id"],
        user_input=TEST_HALO_DATA_SELECT_PAGE,
    )
    assert result_page["type"] is FlowResultType.FORM
    assert result_page["step_id"] == HALO_OPTION_PAGE

    # Remove the second button
    result_modify_page = await hass.config_entries.options.async_configure(
        flow_id=result_page["flow_id"],
        user_input=TEST_HALO_DATA_PAGE,
    )
    assert result_modify_page["type"] is FlowResultType.FORM
    assert result_modify_page["step_id"] == "button"

    # Configure the existing button
    result_button = await hass.config_entries.options.async_configure(
        flow_id=result_page["flow_id"],
        user_input=TEST_HALO_DATA_BUTTON,
    )
    assert result_button["type"] is FlowResultType.CREATE_ENTRY
    assert result_button["data"] == TEST_HALO_DATA_CREATE_ENTRY_WITH_CONFIGURATION


async def test_halo_config_flow_options_add_button(
    hass: HomeAssistant, integration_halo: None, mock_config_entry_halo: MockConfigEntry
) -> None:
    """Test Halo options by adding a button to an existing page."""

    # Start options
    result_init = await hass.config_entries.options.async_init(
        mock_config_entry_halo.entry_id
    )
    assert result_init["type"] is FlowResultType.MENU
    assert result_init["step_id"] == "init"
    # Ensure only the expected options are available
    assert result_init["menu_options"] == [
        HALO_OPTION_PAGE,
        HALO_OPTION_MODIFY_PAGE,
        HALO_OPTION_DELETE_PAGES,
        HALO_OPTION_MODIFY_DEFAULT,
    ]
    # Select "Modify an existing page"
    result_options = await hass.config_entries.options.async_configure(
        flow_id=result_init["flow_id"],
        user_input={"next_step_id": HALO_OPTION_MODIFY_PAGE},
    )
    assert result_options["type"] is FlowResultType.FORM
    assert result_options["step_id"] == HALO_OPTION_MODIFY_PAGE
    # Ensure only the expected options are available
    assert result_options["data_schema"].schema["pages"].config["options"] == [
        TEST_HALO_PAGE
    ]

    # Select page
    result_page = await hass.config_entries.options.async_configure(
        flow_id=result_options["flow_id"],
        user_input=TEST_HALO_DATA_SELECT_PAGE,
    )
    assert result_page["type"] is FlowResultType.FORM
    assert result_page["step_id"] == HALO_OPTION_PAGE

    # Add an additional button
    result_modify_page = await hass.config_entries.options.async_configure(
        flow_id=result_page["flow_id"],
        user_input=TEST_HALO_DATA_PAGE_2_BUTTONS,
    )
    assert result_modify_page["type"] is FlowResultType.FORM
    assert result_modify_page["step_id"] == "button"

    # Configure existing button (1)
    # For pre-existing buttons, the current configuration will be the "default" values in the form
    result_button = await hass.config_entries.options.async_configure(
        flow_id=result_page["flow_id"],
        user_input=TEST_HALO_DATA_BUTTON,
    )
    assert result_button["type"] is FlowResultType.FORM
    assert result_button["step_id"] == "button"

    # Configure new button (2)
    with patch(TEST_HALO_UUID_TARGET, return_value=TEST_HALO_BUTTON_2_ID):
        result_button_2 = await hass.config_entries.options.async_configure(
            flow_id=result_button["flow_id"],
            user_input=TEST_HALO_DATA_BUTTON_2,
        )
    assert result_button_2["type"] is FlowResultType.CREATE_ENTRY
    assert (
        result_button_2["data"]
        == TEST_HALO_DATA_CREATE_ENTRY_WITH_CONFIGURATION_2_BUTTONS
    )


async def test_halo_config_flow_options_add_default(
    hass: HomeAssistant,
    integration_halo: None,
    mock_config_entry_halo: MockConfigEntry,
) -> None:
    """Test Halo options by adding a default button."""

    # Start options
    result_init = await hass.config_entries.options.async_init(
        mock_config_entry_halo.entry_id
    )
    assert result_init["type"] is FlowResultType.MENU
    assert result_init["step_id"] == "init"
    # Ensure only the expected options are available
    assert result_init["menu_options"] == [
        HALO_OPTION_PAGE,
        HALO_OPTION_MODIFY_PAGE,
        HALO_OPTION_DELETE_PAGES,
        HALO_OPTION_MODIFY_DEFAULT,
    ]

    # Select "Modify default button"
    result_options = await hass.config_entries.options.async_configure(
        flow_id=result_init["flow_id"],
        user_input={"next_step_id": HALO_OPTION_MODIFY_DEFAULT},
    )
    assert result_options["type"] is FlowResultType.MENU
    assert result_options["step_id"] == HALO_OPTION_MODIFY_DEFAULT
    assert result_options["menu_options"] == [HALO_OPTION_SELECT_DEFAULT]

    # Select the "Select the default button" option
    result_modify_default = await hass.config_entries.options.async_configure(
        flow_id=result_options["flow_id"],
        user_input={"next_step_id": HALO_OPTION_SELECT_DEFAULT},
    )
    assert result_modify_default["type"] is FlowResultType.FORM
    assert result_modify_default["step_id"] == HALO_OPTION_SELECT_DEFAULT

    # Proceed without changing default values
    result_select_default = await hass.config_entries.options.async_configure(
        flow_id=result_modify_default["flow_id"],
        user_input=TEST_HALO_DATA_SELECT_DEFAULT,
    )
    assert result_select_default["type"] is FlowResultType.CREATE_ENTRY
    assert (
        result_select_default["data"]
        == TEST_HALO_DATA_CREATE_ENTRY_WITH_CONFIGURATION_DEFAULT
    )


async def test_halo_config_flow_options_remove_default(hass: HomeAssistant) -> None:
    """Test Halo options by removing a default button."""
    # Setup Halo with a default selected
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEST_HALO_SERIAL,
        data=TEST_HALO_DATA_CREATE_ENTRY,
        options=TEST_HALO_DATA_CREATE_ENTRY_WITH_CONFIGURATION_DEFAULT,
        title=TEST_HALO_NAME,
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Start options
    result_init = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result_init["type"] is FlowResultType.MENU
    assert result_init["step_id"] == "init"
    # Ensure only the expected options are available
    assert result_init["menu_options"] == [
        HALO_OPTION_PAGE,
        HALO_OPTION_MODIFY_PAGE,
        HALO_OPTION_DELETE_PAGES,
        HALO_OPTION_MODIFY_DEFAULT,
    ]

    # Select "Modify default button"
    result_options = await hass.config_entries.options.async_configure(
        flow_id=result_init["flow_id"],
        user_input={"next_step_id": HALO_OPTION_MODIFY_DEFAULT},
    )
    assert result_options["type"] is FlowResultType.MENU
    assert result_options["step_id"] == HALO_OPTION_MODIFY_DEFAULT
    # Only one button is available in the configuration and it is already default,
    # so only the remove option is available
    assert result_options["menu_options"] == [HALO_OPTION_REMOVE_DEFAULT]

    # Select the "Remove the default attribute from {button}" option
    result_remove_default = await hass.config_entries.options.async_configure(
        flow_id=result_options["flow_id"],
        user_input={"next_step_id": HALO_OPTION_REMOVE_DEFAULT},
    )
    assert result_remove_default["type"] is FlowResultType.CREATE_ENTRY
    assert (
        result_remove_default["data"] == TEST_HALO_DATA_CREATE_ENTRY_WITH_CONFIGURATION
    )
