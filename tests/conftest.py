"""Test fixtures for bang_olufsen."""

from collections.abc import Generator
from copy import deepcopy
from unittest.mock import AsyncMock, Mock, patch

from mozart_api import BeolinkJoinResult, Preset, Scene
from mozart_api.models import (
    Action,
    BatteryState,
    BeolinkPeer,
    BeolinkSelf,
    ContentItem,
    ListeningMode,
    ListeningModeFeatures,
    ListeningModeRef,
    ListeningModeTrigger,
    PairedRemote,
    PairedRemoteResponse,
    PlaybackContentMetadata,
    PlaybackProgress,
    PlaybackState,
    PlayQueueSettings,
    ProductState,
    RemoteMenuItem,
    RenderingState,
    SoftwareUpdateState,
    SoftwareUpdateStatus,
    Source,
    SourceArray,
    SourceTypeEnum,
    VolumeState,
)
import pytest

from homeassistant.components.bang_olufsen.const import DOMAIN
from homeassistant.core import HomeAssistant

from .const import (
    TEST_DATA_CREATE_ENTRY,
    TEST_DATA_CREATE_ENTRY_2,
    TEST_DATA_CREATE_ENTRY_3,
    TEST_FRIENDLY_NAME,
    TEST_FRIENDLY_NAME_3,
    TEST_FRIENDLY_NAME_4,
    TEST_HALO_BUTTON_2_ID,
    TEST_HALO_BUTTON_ID,
    TEST_HALO_CONFIGURATION_ID,
    TEST_HALO_DATA_CREATE_ENTRY,
    TEST_HALO_DATA_CREATE_ENTRY_WITH_CONFIGURATION,
    TEST_HALO_NAME,
    TEST_HALO_PAGE_ID,
    TEST_HALO_SERIAL,
    TEST_HALO_UUID_TARGET,
    TEST_HOST_3,
    TEST_HOST_4,
    TEST_JID_1,
    TEST_JID_3,
    TEST_JID_4,
    TEST_NAME,
    TEST_NAME_2,
    TEST_NAME_3,
    TEST_REMOTE_SERIAL,
    TEST_SERIAL_NUMBER,
    TEST_SERIAL_NUMBER_2,
    TEST_SERIAL_NUMBER_3,
    TEST_SOUND_MODE,
    TEST_SOUND_MODE_2,
    TEST_SOUND_MODE_NAME,
)

from tests.common import MockConfigEntry


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Mock config entry for Beosound Balance."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEST_SERIAL_NUMBER,
        data=TEST_DATA_CREATE_ENTRY,
        title=TEST_NAME,
    )


@pytest.fixture
def mock_config_entry_core() -> MockConfigEntry:
    """Mock config entry for Beoconnect Core."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEST_SERIAL_NUMBER_2,
        data=TEST_DATA_CREATE_ENTRY_2,
        title=TEST_NAME_2,
    )


@pytest.fixture
def mock_config_entry_level() -> MockConfigEntry:
    """Mock config entry for Beosound Level."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEST_SERIAL_NUMBER_3,
        data=TEST_DATA_CREATE_ENTRY_3,
        title=TEST_NAME_3,
    )


@pytest.fixture
def mock_config_entry_halo() -> MockConfigEntry:
    """Mock config entry for Beoremote Halo."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEST_HALO_SERIAL,
        data=TEST_HALO_DATA_CREATE_ENTRY,
        options=deepcopy(TEST_HALO_DATA_CREATE_ENTRY_WITH_CONFIGURATION),
        title=TEST_HALO_NAME,
    )


async def mock_websocket_connection(
    hass: HomeAssistant, mock_mozart_client: AsyncMock
) -> None:
    """Register and receive initial WebSocket notifications."""

    # Currently only add notifications that are used.

    # Register callbacks.
    volume_callback = mock_mozart_client.get_volume_notifications.call_args[0][0]
    source_change_callback = (
        mock_mozart_client.get_source_change_notifications.call_args[0][0]
    )
    playback_state_callback = (
        mock_mozart_client.get_playback_state_notifications.call_args[0][0]
    )
    playback_metadata_callback = (
        mock_mozart_client.get_playback_metadata_notifications.call_args[0][0]
    )

    # Trigger callbacks. Try to use existing data
    volume_callback(mock_mozart_client.get_product_state.return_value.volume)
    source_change_callback(
        mock_mozart_client.get_product_state.return_value.playback.source
    )
    playback_state_callback(
        mock_mozart_client.get_product_state.return_value.playback.state
    )
    playback_metadata_callback(
        mock_mozart_client.get_product_state.return_value.playback.metadata
    )
    await hass.async_block_till_done()


@pytest.fixture(name="integration")
async def integration_fixture(
    hass: HomeAssistant,
    mock_mozart_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Set up the Bang & Olufsen integration."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await mock_websocket_connection(hass, mock_mozart_client)


@pytest.fixture(name="integration_halo")
async def integration_halo_fixture(
    hass: HomeAssistant,
    mock_halo_client: AsyncMock,
    mock_config_entry_halo: MockConfigEntry,
) -> None:
    """Set up the Bang & Olufsen integration with a Beoremote Halo with initial configuration."""

    mock_config_entry_halo.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry_halo.entry_id)
    await hass.async_block_till_done()


@pytest.fixture
def mock_halo_uuid() -> Generator[AsyncMock]:
    """Mock _halo_uuid() to get predictable output."""
    with patch(
        TEST_HALO_UUID_TARGET,
        side_effect=[
            TEST_HALO_CONFIGURATION_ID,
            TEST_HALO_PAGE_ID,
            TEST_HALO_BUTTON_ID,
            TEST_HALO_BUTTON_2_ID,
        ],
    ):
        yield


@pytest.fixture
def mock_mozart_client() -> Generator[AsyncMock]:
    """Mock MozartClient."""
    with (
        patch(
            "homeassistant.components.bang_olufsen.MozartClient", autospec=True
        ) as mock_client,
        patch(
            "homeassistant.components.bang_olufsen.config_flow.MozartClient",
            new=mock_client,
        ),
    ):
        client = mock_client.return_value

        # REST API client methods
        client.get_beolink_self = AsyncMock()
        client.get_beolink_self.return_value = BeolinkSelf(
            friendly_name=TEST_FRIENDLY_NAME, jid=TEST_JID_1
        )
        client.get_softwareupdate_status = AsyncMock()
        client.get_softwareupdate_status.return_value = SoftwareUpdateStatus(
            software_version="1.0.0", state=SoftwareUpdateState()
        )
        client.get_product_state = AsyncMock()
        client.get_product_state.return_value = ProductState(
            volume=VolumeState(),
            playback=PlaybackState(
                metadata=PlaybackContentMetadata(),
                progress=PlaybackProgress(),
                source=Source(),
                state=RenderingState(value="started"),
            ),
        )
        client.get_available_sources = AsyncMock()
        client.get_available_sources.return_value = SourceArray(
            items=[
                # Is not playable, so should not be user selectable
                Source(
                    name="AirPlay",
                    id="airPlay",
                    is_enabled=True,
                    is_multiroom_available=False,
                ),
                # The only available beolink source
                Source(
                    name="Tidal",
                    id="tidal",
                    is_enabled=True,
                    is_multiroom_available=True,
                    is_playable=True,
                ),
                Source(
                    name="Line-In",
                    id="lineIn",
                    is_enabled=True,
                    is_multiroom_available=False,
                    is_playable=True,
                ),
                # Is disabled and not playable, so should not be user selectable
                Source(
                    name="Powerlink",
                    id="pl",
                    is_enabled=False,
                ),
            ]
        )
        client.get_remote_menu = AsyncMock()
        client.get_remote_menu.return_value = {
            # Music category, so shouldn't be included in video sources
            "b355888b-2cde-5f94-8592-d47b71d52a27": RemoteMenuItem(
                action_list=[
                    Action(
                        button_name=None,
                        content_id="netRadio://6629967157728971",
                        deezer_user_id=None,
                        gain_db=None,
                        listening_mode_id=None,
                        preset_key=None,
                        queue_item=None,
                        queue_settings=None,
                        radio_station_id=None,
                        source=None,
                        speaker_group_id=None,
                        stand_position=None,
                        stop_duration=None,
                        tone_name=None,
                        type="triggerContent",
                        volume_level=None,
                    )
                ],
                scene_list=None,
                disabled=None,
                dynamic_list=None,
                first_child_menu_item_id=None,
                label="Yle Radio Suomi Helsinki",
                next_sibling_menu_item_id="0b4552f8-7ac6-5046-9d44-5410a815b8d6",
                parent_menu_item_id="eee0c2d0-2b3a-4899-a708-658475c38926",
                available=None,
                content=ContentItem(
                    categories=["music"],
                    content_uri="netRadio://6629967157728971",
                    label="Yle Radio Suomi Helsinki",
                    source=SourceTypeEnum(value="netRadio"),
                ),
                fixed=True,
                id="b355888b-2cde-5f94-8592-d47b71d52a27",
            ),
            # Has "hdmi" as category, so should be included in video sources
            "b6591565-80f4-4356-bcd9-c92ca247f0a9": RemoteMenuItem(
                action_list=[
                    Action(
                        button_name=None,
                        content_id="tv://hdmi_1",
                        deezer_user_id=None,
                        gain_db=None,
                        listening_mode_id=None,
                        preset_key=None,
                        queue_item=None,
                        queue_settings=None,
                        radio_station_id=None,
                        source=None,
                        speaker_group_id=None,
                        stand_position=None,
                        stop_duration=None,
                        tone_name=None,
                        type="triggerContent",
                        volume_level=None,
                    )
                ],
                scene_list=None,
                disabled=False,
                dynamic_list="none",
                first_child_menu_item_id=None,
                label="HDMI A",
                next_sibling_menu_item_id="0ba98974-7b1f-40dc-bc48-fbacbb0f1793",
                parent_menu_item_id="b66c835b-6b98-4400-8f84-6348043792c7",
                available=True,
                content=ContentItem(
                    categories=["hdmi"],
                    content_uri="tv://hdmi_1",
                    label="HDMI A",
                    source=SourceTypeEnum(value="tv"),
                ),
                fixed=False,
                id="b6591565-80f4-4356-bcd9-c92ca247f0a9",
            ),
            # The parent remote menu item. Has the TV label and should therefore not be included in video sources
            "b66c835b-6b98-4400-8f84-6348043792c7": RemoteMenuItem(
                action_list=[],
                scene_list=None,
                disabled=False,
                dynamic_list="none",
                first_child_menu_item_id="b6591565-80f4-4356-bcd9-c92ca247f0a9",
                label="TV",
                next_sibling_menu_item_id="0c4547fe-d3cc-4348-a425-473595b8c9fb",
                parent_menu_item_id=None,
                available=True,
                content=None,
                fixed=True,
                id="b66c835b-6b98-4400-8f84-6348043792c7",
            ),
            # Has an empty content, so should not be included
            "64c9da45-3682-44a4-8030-09ed3ef44160": RemoteMenuItem(
                action_list=[],
                scene_list=None,
                disabled=False,
                dynamic_list="none",
                first_child_menu_item_id=None,
                label="ListeningPosition",
                next_sibling_menu_item_id=None,
                parent_menu_item_id="0c4547fe-d3cc-4348-a425-473595b8c9fb",
                available=True,
                content=None,
                fixed=True,
                id="64c9da45-3682-44a4-8030-09ed3ef44160",
            ),
        }
        client.get_beolink_peers = AsyncMock()
        client.get_beolink_peers.return_value = [
            BeolinkPeer(
                friendly_name=TEST_FRIENDLY_NAME_3,
                jid=TEST_JID_3,
                ip_address=TEST_HOST_3,
            ),
            BeolinkPeer(
                friendly_name=TEST_FRIENDLY_NAME_4,
                jid=TEST_JID_4,
                ip_address=TEST_HOST_4,
            ),
        ]
        client.get_beolink_listeners = AsyncMock()
        client.get_beolink_listeners.return_value = [
            BeolinkPeer(
                friendly_name=TEST_FRIENDLY_NAME_3,
                jid=TEST_JID_3,
                ip_address=TEST_HOST_3,
            ),
            BeolinkPeer(
                friendly_name=TEST_FRIENDLY_NAME_4,
                jid=TEST_JID_4,
                ip_address=TEST_HOST_4,
            ),
        ]

        client.get_listening_mode_set = AsyncMock()
        client.get_listening_mode_set.return_value = [
            ListeningMode(
                id=TEST_SOUND_MODE,
                name=TEST_SOUND_MODE_NAME,
                features=ListeningModeFeatures(),
                triggers=[ListeningModeTrigger()],
            ),
            ListeningMode(
                id=TEST_SOUND_MODE_2,
                name=TEST_SOUND_MODE_NAME,
                features=ListeningModeFeatures(),
                triggers=[ListeningModeTrigger()],
            ),
            ListeningMode(
                id=345,
                name=f"{TEST_SOUND_MODE_NAME} 2",
                features=ListeningModeFeatures(),
                triggers=[ListeningModeTrigger()],
            ),
        ]
        client.get_active_listening_mode = AsyncMock()
        client.get_active_listening_mode.return_value = ListeningModeRef(
            href="",
            id=123,
        )
        client.get_settings_queue = AsyncMock()
        client.get_settings_queue.return_value = PlayQueueSettings(
            repeat="none",
            shuffle=False,
        )
        client.get_bluetooth_remotes = AsyncMock()
        client.get_bluetooth_remotes.return_value = PairedRemoteResponse(
            items=[
                PairedRemote(
                    address="",
                    app_version="1.0.0",
                    battery_level=50,
                    connected=True,
                    serial_number=TEST_REMOTE_SERIAL,
                    name="BEORC",
                )
            ]
        )
        client.get_battery_state = AsyncMock()
        client.get_battery_state.return_value = BatteryState(
            battery_level=0,
            is_charging=False,
            remaining_charging_time_minutes=0,
            remaining_playing_time_minutes=0,
        )
        client.get_all_scenes = AsyncMock()
        client.get_all_scenes.return_value = {
            "0df8fa2e-433d-473c-bb67-62ed88279ba2": Scene(
                action_list=[
                    Action(
                        preset_key="Preset1",
                        source=Source(value="spotify"),
                        type="sourcePreset",
                    )
                ],
                classification="system",
            )
        }
        client.get_presets = AsyncMock()
        client.get_presets.return_value = {
            "1": Preset(
                action_list=[
                    Action(
                        preset_key="Preset1",
                        source=Source(value="spotify"),
                        type="sourcePreset",
                    )
                ],
                content=ContentItem(
                    categories=["music"],
                    content_uri="spotify",
                    label="Spotify Connect",
                    source=Source(value="spotify"),
                ),
            )
        }
        client.get_beolink_join_result = AsyncMock()
        client.get_beolink_join_result.return_value = BeolinkJoinResult(
            error=None,
            jid=TEST_JID_1,
            request_id="0123456-789a-bcde-f012-3456789abcde",
            status="joined",
            type="join",
        )

        client.post_standby = AsyncMock()
        client.set_current_volume_level = AsyncMock()
        client.set_volume_mute = AsyncMock()
        client.post_playback_command = AsyncMock()
        client.seek_to_position = AsyncMock()
        client.post_clear_queue = AsyncMock()
        client.post_overlay_play = AsyncMock()
        client.post_uri_source = AsyncMock()
        client.run_provided_scene = AsyncMock()
        client.activate_preset = AsyncMock()
        client.start_deezer_flow = AsyncMock()
        client.add_to_queue = AsyncMock()
        client.post_remote_trigger = AsyncMock()
        client.set_active_source = AsyncMock()
        client.post_beolink_expand = AsyncMock()
        client.join_beolink_peer = AsyncMock()
        client.post_beolink_unexpand = AsyncMock()
        client.post_beolink_leave = AsyncMock()
        client.post_beolink_allstandby = AsyncMock()
        client.join_latest_beolink_experience = AsyncMock()
        client.activate_listening_mode = AsyncMock()
        client.set_settings_queue = AsyncMock()

        # REST API client helper methods
        client.async_get_beolink_join_result = AsyncMock()
        client.async_get_beolink_join_result.return_value = BeolinkJoinResult(
            error=None,
            jid=TEST_JID_1,
            request_id="0123456-789a-bcde-f012-3456789abcde",
            status="joined",
            type="join",
        )
        client.async_post_beolink_expand = AsyncMock()
        client.async_post_beolink_expand.return_value = True

        # Non-REST API client methods
        client.check_device_connection = AsyncMock()
        client.close_api_client = AsyncMock()

        # WebSocket listener
        client.connect_notifications = AsyncMock()
        client.disconnect_notifications = Mock()
        client.websocket_connected = False

        yield client


@pytest.fixture
def mock_halo_client() -> Generator[AsyncMock]:
    """Mock Halo."""
    with patch(
        "homeassistant.components.bang_olufsen.Halo", autospec=True
    ) as mock_client:
        client = mock_client.return_value

        # WebSocket methods
        client.update = AsyncMock()
        client.check_device_connection = AsyncMock()
        client.connect = AsyncMock()
        client.disconnect = AsyncMock()
        client.websocket_connected = True

        yield client


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Mock successful setup entry."""
    with patch(
        "homeassistant.components.bang_olufsen.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry
