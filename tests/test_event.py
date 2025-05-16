"""Test the bang_olufsen event entities."""

from unittest.mock import AsyncMock

from mozart_api import WebsocketNotificationTag
from mozart_api.models import BeoRemoteButton, ButtonEvent, PairedRemoteResponse
from pytest_unordered import unordered
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.bang_olufsen.beoremote_halo.models import (
    SystemEvent,
    SystemEventState,
)
from homeassistant.components.bang_olufsen.const import (
    BEO_REMOTE_KEY_EVENTS,
    DEVICE_BUTTON_EVENTS,
    EVENT_TRANSLATION_MAP,
    WebsocketNotification,
)
from homeassistant.components.event import ATTR_EVENT_TYPE, ATTR_EVENT_TYPES
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import EntityRegistry

from .conftest import mock_websocket_connection
from .const import (
    TEST_BUTTON_EVENT_ENTITY_ID,
    TEST_HALO_SYSTEM_STATUS_EVENT_ENTITY_ID,
    TEST_PROXIMITY_EVENT_ENTITY_ID,
    TEST_REMOTE_KEY_EVENT_ENTITY_ID,
)
from .util import get_balance_entity_ids, get_remote_entity_ids

from tests.common import MockConfigEntry

# Mozart related tests


async def test_button_and_key_event_creation(
    hass: HomeAssistant,
    integration: None,
    entity_registry: EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test button and remote key event entities are created."""
    # Add Beosound Balance and remote entity ids
    entity_ids: list[str] = [*get_balance_entity_ids(), *get_remote_entity_ids()]

    # Check that the entities are available
    for entity_id in entity_ids:
        assert entity_registry.async_get(entity_id)

    # Check created entities
    entity_ids_available = list(entity_registry.entities.keys())
    assert entity_ids_available == unordered(entity_ids)

    # Check snapshot
    assert entity_ids_available == snapshot


async def test_no_button_and_remote_key_event_creation(
    hass: HomeAssistant,
    mock_config_entry_core: MockConfigEntry,
    mock_mozart_client: AsyncMock,
    entity_registry: EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test button event entities are not created when using a Beoconnect Core with no Beoremote One connected."""
    mock_mozart_client.get_bluetooth_remotes.return_value = PairedRemoteResponse(
        items=[]
    )

    # Load entry
    mock_config_entry_core.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry_core.entry_id)
    await mock_websocket_connection(hass, mock_mozart_client)

    # Check number of entities
    # The media_player entity should be the only available
    entity_ids_available = list(entity_registry.entities.keys())
    assert len(entity_ids_available) == 1

    # Check snapshot
    assert entity_ids_available == snapshot


async def test_button(
    hass: HomeAssistant,
    integration: None,
    mock_config_entry: MockConfigEntry,
    mock_mozart_client: AsyncMock,
    entity_registry: EntityRegistry,
) -> None:
    """Test button event entity."""

    # Enable the entity
    entity_registry.async_update_entity(TEST_BUTTON_EVENT_ENTITY_ID, disabled_by=None)
    hass.config_entries.async_schedule_reload(mock_config_entry.entry_id)

    assert (states := hass.states.get(TEST_BUTTON_EVENT_ENTITY_ID))
    assert states.state is STATE_UNKNOWN
    assert states.attributes[ATTR_EVENT_TYPES] == list(DEVICE_BUTTON_EVENTS)

    # Check button reacts as expected to WebSocket events
    notification_callback = mock_mozart_client.get_button_notifications.call_args[0][0]

    notification_callback(ButtonEvent(button="PlayPause", state="shortPress (Release)"))
    await hass.async_block_till_done()

    assert (states := hass.states.get(TEST_BUTTON_EVENT_ENTITY_ID))
    assert states.state is not None
    assert (
        states.attributes[ATTR_EVENT_TYPE]
        == EVENT_TRANSLATION_MAP["shortPress (Release)"]
    )


async def test_remote_key(
    hass: HomeAssistant,
    integration: None,
    mock_config_entry: MockConfigEntry,
    mock_mozart_client: AsyncMock,
    entity_registry: EntityRegistry,
) -> None:
    """Test remote key event entity."""

    # Enable the entity
    entity_registry.async_update_entity(
        TEST_REMOTE_KEY_EVENT_ENTITY_ID, disabled_by=None
    )
    hass.config_entries.async_schedule_reload(mock_config_entry.entry_id)

    assert (states := hass.states.get(TEST_REMOTE_KEY_EVENT_ENTITY_ID))
    assert states.state is STATE_UNKNOWN
    assert states.attributes[ATTR_EVENT_TYPES] == list(BEO_REMOTE_KEY_EVENTS)

    # Check button reacts as expected to WebSocket events
    notification_callback = (
        mock_mozart_client.get_beo_remote_button_notifications.call_args[0][0]
    )

    notification_callback(BeoRemoteButton(key="Control/Play", type="KeyPress"))
    await hass.async_block_till_done()

    assert (states := hass.states.get(TEST_REMOTE_KEY_EVENT_ENTITY_ID))
    assert states.state is not None
    assert states.attributes[ATTR_EVENT_TYPE] == EVENT_TRANSLATION_MAP["KeyPress"]


async def test_proximity(
    hass: HomeAssistant,
    integration: None,
    mock_config_entry: MockConfigEntry,
    mock_mozart_client: AsyncMock,
    entity_registry: EntityRegistry,
) -> None:
    """Test proximity event entity."""

    # Enable the entity
    entity_registry.async_update_entity(
        TEST_PROXIMITY_EVENT_ENTITY_ID, disabled_by=None
    )
    hass.config_entries.async_schedule_reload(mock_config_entry.entry_id)

    assert (states := hass.states.get(TEST_PROXIMITY_EVENT_ENTITY_ID))
    assert states.state is STATE_UNKNOWN

    # Check entity reacts as expected to WebSocket events
    proximity_callback = mock_mozart_client.get_notification_notifications.call_args[0][
        0
    ]

    await proximity_callback(
        WebsocketNotificationTag(
            value=WebsocketNotification.PROXIMITY_PRESENCE_DETECTED.value
        )
    )
    await hass.async_block_till_done()

    assert (states := hass.states.get(TEST_PROXIMITY_EVENT_ENTITY_ID))
    assert states.state is not None
    assert (
        states.attributes[ATTR_EVENT_TYPE]
        == EVENT_TRANSLATION_MAP[WebsocketNotification.PROXIMITY_PRESENCE_DETECTED]
    )


# Halo related tests


async def test_halo_system_status(
    hass: HomeAssistant,
    integration_halo: None,
    mock_config_entry_halo: MockConfigEntry,
    mock_halo_client: AsyncMock,
    entity_registry: EntityRegistry,
) -> None:
    """Test Halo system status event entity."""
    assert (states := hass.states.get(TEST_HALO_SYSTEM_STATUS_EVENT_ENTITY_ID))
    assert states.state is STATE_UNKNOWN

    # Check entity reacts as expected to WebSocket events
    system_callback = mock_halo_client.get_system_event.call_args[0][0]

    system_callback(SystemEvent(state=SystemEventState.ACTIVE.value))
    await hass.async_block_till_done()

    assert (states := hass.states.get(TEST_HALO_SYSTEM_STATUS_EVENT_ENTITY_ID))
    assert states.state is not None
    assert states.attributes[ATTR_EVENT_TYPE] == SystemEventState.ACTIVE.value
