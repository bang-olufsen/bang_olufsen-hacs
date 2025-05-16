"""Test the bang_olufsen binary sensor entities."""

from unittest.mock import AsyncMock

from mozart_api.models import BatteryState

from homeassistant.components.bang_olufsen.beoremote_halo.models import (
    PowerEvent,
    PowerEventState,
)
from homeassistant.core import HomeAssistant

from .conftest import mock_websocket_connection
from .const import (
    TEST_BATTERY_CHARGING_BINARY_SENSOR_ENTITY_ID,
    TEST_HALO_BATTERY_CHARGING_BINARY_SENSOR_ENTITY_ID,
)

from tests.common import MockConfigEntry

# Mozart related tests


async def test_battery_charging(
    hass: HomeAssistant,
    mock_mozart_client: AsyncMock,
    mock_config_entry_level: MockConfigEntry,
) -> None:
    """Test the battery charging time entity."""
    # Ensure battery entities are created
    mock_mozart_client.get_battery_state.return_value = BatteryState(battery_level=1)

    # Load entry
    mock_config_entry_level.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry_level.entry_id)
    await mock_websocket_connection(hass, mock_mozart_client)
    await hass.async_block_till_done()

    # Initial state is False
    assert (states := hass.states.get(TEST_BATTERY_CHARGING_BINARY_SENSOR_ENTITY_ID))
    assert states.state == "off"

    # Check binary sensor reacts as expected to WebSocket events
    battery_callback = mock_mozart_client.get_battery_notifications.call_args[0][0]

    battery_callback(BatteryState(is_charging=True))
    await hass.async_block_till_done()

    assert (states := hass.states.get(TEST_BATTERY_CHARGING_BINARY_SENSOR_ENTITY_ID))
    assert states.state == "on"


# Halo related tests


async def test_halo_battery_charging(
    hass: HomeAssistant,
    integration_halo: None,
    mock_halo_client: AsyncMock,
) -> None:
    """Test the Halo battery charging time entity."""

    # Initial state is False
    assert (
        states := hass.states.get(TEST_HALO_BATTERY_CHARGING_BINARY_SENSOR_ENTITY_ID)
    )
    assert states.state == "off"

    # Check binary sensor reacts as expected to WebSocket events
    battery_callback = mock_halo_client.get_power_event.call_args[0][0]

    battery_callback(PowerEvent(capacity=50, state=PowerEventState.CHARGING.value))

    assert (
        states := hass.states.get(TEST_HALO_BATTERY_CHARGING_BINARY_SENSOR_ENTITY_ID)
    )
    assert states.state == "on"
