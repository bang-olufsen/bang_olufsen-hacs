"""Test the bang_olufsen sensor entities."""

from unittest.mock import AsyncMock

from mozart_api.models import BatteryState
import pytest

from homeassistant.components.bang_olufsen.beoremote_halo.models import (
    PowerEvent,
    PowerEventState,
)
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import EntityRegistry

from .conftest import mock_websocket_connection
from .const import (
    TEST_BATTERY_CHARGING_TIME_SENSOR_ENTITY_ID,
    TEST_BATTERY_LEVEL_SENSOR_ENTITY_ID,
    TEST_BATTERY_PLAYING_TIME_SENSOR_ENTITY_ID,
    TEST_HALO_BATTERY_SENSOR_ENTITY_ID,
)

from tests.common import MockConfigEntry

# Mozart related tests


@pytest.mark.parametrize(
    ("charging_time", "expected_value"),
    [
        # Device is charging
        (100, "100"),
        # Device is not charging
        (65535, "0"),
    ],
)
async def test_battery_charging_time(
    hass: HomeAssistant,
    mock_mozart_client: AsyncMock,
    mock_config_entry_level: MockConfigEntry,
    entity_registry: EntityRegistry,
    charging_time: int,
    expected_value: str,
) -> None:
    """Test the battery charging time entity."""
    # Ensure battery entities are created
    mock_mozart_client.get_battery_state.return_value = BatteryState(battery_level=1)

    # Load entry
    mock_config_entry_level.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry_level.entry_id)
    await mock_websocket_connection(hass, mock_mozart_client)
    await hass.async_block_till_done()

    # Enable the entity
    entity_registry.async_update_entity(
        TEST_BATTERY_CHARGING_TIME_SENSOR_ENTITY_ID, disabled_by=None
    )
    hass.config_entries.async_schedule_reload(mock_config_entry_level.entry_id)
    await hass.async_block_till_done()

    assert (states := hass.states.get(TEST_BATTERY_CHARGING_TIME_SENSOR_ENTITY_ID))
    assert states.state is STATE_UNKNOWN

    # Check sensor reacts as expected to WebSocket events
    battery_callback = mock_mozart_client.get_battery_notifications.call_args[0][0]

    battery_callback(BatteryState(remaining_charging_time_minutes=charging_time))
    await hass.async_block_till_done()

    assert (states := hass.states.get(TEST_BATTERY_CHARGING_TIME_SENSOR_ENTITY_ID))
    assert states.state == expected_value


async def test_battery_level(
    hass: HomeAssistant,
    mock_mozart_client: AsyncMock,
    mock_config_entry_level: MockConfigEntry,
    entity_registry: EntityRegistry,
) -> None:
    """Test the battery level entity."""
    # Ensure battery entities are created
    mock_mozart_client.get_battery_state.return_value = BatteryState(battery_level=1)

    # Load entry
    mock_config_entry_level.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry_level.entry_id)
    await mock_websocket_connection(hass, mock_mozart_client)
    await hass.async_block_till_done()

    assert (states := hass.states.get(TEST_BATTERY_LEVEL_SENSOR_ENTITY_ID))
    assert states.state is STATE_UNKNOWN

    # Check sensor reacts as expected to WebSocket events
    battery_callback = mock_mozart_client.get_battery_notifications.call_args[0][0]

    battery_callback(BatteryState(battery_level=50))
    await hass.async_block_till_done()

    assert (states := hass.states.get(TEST_BATTERY_LEVEL_SENSOR_ENTITY_ID))
    assert states.state == "50"


@pytest.mark.parametrize(
    ("playing_time", "expected_value"),
    [
        # Device is charging
        (65535, "0"),
        # Device is not charging
        (100, "100"),
    ],
)
async def test_battery_playing_time(
    hass: HomeAssistant,
    mock_mozart_client: AsyncMock,
    mock_config_entry_level: MockConfigEntry,
    entity_registry: EntityRegistry,
    playing_time: int,
    expected_value: str,
) -> None:
    """Test the battery playing time entity."""
    # Ensure battery entities are created
    mock_mozart_client.get_battery_state.return_value = BatteryState(battery_level=1)

    # Load entry
    mock_config_entry_level.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry_level.entry_id)
    await mock_websocket_connection(hass, mock_mozart_client)
    await hass.async_block_till_done()

    # Enable the entity
    entity_registry.async_update_entity(
        TEST_BATTERY_PLAYING_TIME_SENSOR_ENTITY_ID, disabled_by=None
    )
    hass.config_entries.async_schedule_reload(mock_config_entry_level.entry_id)
    await hass.async_block_till_done()

    assert (states := hass.states.get(TEST_BATTERY_PLAYING_TIME_SENSOR_ENTITY_ID))
    assert states.state is STATE_UNKNOWN

    # Check sensor reacts as expected to WebSocket events
    battery_callback = mock_mozart_client.get_battery_notifications.call_args[0][0]

    battery_callback(BatteryState(remaining_playing_time_minutes=playing_time))
    await hass.async_block_till_done()

    assert (states := hass.states.get(TEST_BATTERY_PLAYING_TIME_SENSOR_ENTITY_ID))
    assert states.state == expected_value


# Halo related tests


async def test_halo_battery_level(
    hass: HomeAssistant,
    integration_halo: None,
    mock_halo_client: AsyncMock,
) -> None:
    """Test the Halo battery entity."""

    assert (states := hass.states.get(TEST_HALO_BATTERY_SENSOR_ENTITY_ID))
    assert states.state is STATE_UNKNOWN

    # Check sensor reacts as expected to WebSocket events
    battery_callback = mock_halo_client.get_power_event.call_args[0][0]

    battery_callback(PowerEvent(capacity=50, state=PowerEventState.CHARGING.value))
    await hass.async_block_till_done()

    assert (states := hass.states.get(TEST_HALO_BATTERY_SENSOR_ENTITY_ID))
    assert states.state == "50"
