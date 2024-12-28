"""WebSocket listener(s) for the Bang & Olufsen integration."""

from __future__ import annotations

from collections.abc import Callable
import contextlib
import logging
from typing import TYPE_CHECKING

from mozart_api.models import (
    BatteryState,
    BeoRemoteButton,
    ButtonEvent,
    ListeningModeProps,
    PlaybackContentMetadata,
    PlaybackError,
    PlaybackProgress,
    RenderingState,
    SoftwareUpdateState,
    Source,
    SpeakerGroupOverview,
    VolumeState,
    WebsocketNotificationTag,
)
from mozart_api.mozart_client import BaseWebSocketResponse, MozartClient
import numpy as np
from voluptuous import Invalid

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN
from homeassistant.components.input_button import DOMAIN as INPUT_BUTTON_DOMAIN
from homeassistant.components.input_number import DOMAIN as INPUT_NUMBER_DOMAIN
from homeassistant.components.number import (
    ATTR_MAX,
    ATTR_MIN,
    ATTR_STEP,
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN, SERVICE_TOGGLE
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, CONF_ENTITY_ID, STATE_ON
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util.enum import try_parse_enum

from .const import (
    CONF_ENTITY_MAP,
    CONF_HALO,
    CONNECTION_STATUS,
    EVENT_TRANSLATION_MAP,
    HALO_WEBSOCKET_EVENT,
    MOZART_WEBSOCKET_EVENT,
    BangOlufsenModel,
    WebsocketNotification,
)
from .entity import HaloBase, MozartBase
from .halo import (
    MAX_VALUE,
    MIN_VALUE,
    BaseConfiguration,
    BaseUpdate,
    BaseWebSocketResponse as HaloBaseWebSocketResponse,
    Button,
    ButtonEvent as HaloButtonEvent,
    ButtonEventState,
    ButtonState,
    Halo,
    PowerEvent,
    StatusEvent,
    SystemEvent,
    UpdateButton,
    WheelEvent,
)
from .util import get_remotes

_LOGGER = logging.getLogger(__name__)


class HaloWebsocket(HaloBase):
    """WebSocket for Halo."""

    _configuration: BaseConfiguration | None = None
    _entity_map: dict[str, str] = {}

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: Halo,
    ) -> None:
        """Initialize the entity coordinator."""
        super().__init__(config_entry, client)

        self.hass = hass
        self._device = self.get_device(hass, self._unique_id)
        self._entity_registry = er.async_get(self.hass)

        if TYPE_CHECKING:
            assert isinstance(self._client, Halo)

        self._client.get_button_event(self.on_button_event)
        self._client.get_on_connection_lost(self.on_connection_lost)
        self._client.get_on_connection(self.on_connection)
        self._client.get_power_event(self.on_power_event)
        self._client.get_status_event(self.on_status_event)
        self._client.get_system_event(self.on_system_event)
        self._client.get_wheel_event(self.on_wheel_event)

        self._client.get_all_events_raw(self.on_all_events_raw)

        # Track entity changes to sync with Halo configuration
        if config_entry.options:
            self._entity_map = config_entry.options[CONF_ENTITY_MAP]

            entity_ids = list(self._entity_map.values())
            async_track_state_change_event(
                self.hass,
                entity_ids,
                self._handle_entity_state_change,
            )
            # Handle configuration
            self._configuration = BaseConfiguration.from_dict(
                self.entry.options[CONF_HALO]
            )

        # Dict for associating platforms with update methods
        self._entity_update_map: dict[str, Callable] = {
            SENSOR_DOMAIN: self._handle_number_update,
            NUMBER_DOMAIN: self._handle_number_update,
            INPUT_NUMBER_DOMAIN: self._handle_number_update,
            SWITCH_DOMAIN: self._handle_binary_update,
            INPUT_BOOLEAN_DOMAIN: self._handle_binary_update,
            BINARY_SENSOR_DOMAIN: self._handle_binary_update,
            BUTTON_DOMAIN: self._handle_button_update,
            INPUT_BUTTON_DOMAIN: self._handle_button_update,
        }

        # Dict for associating platforms with update methods
        self._entity_button_action_map: dict[str, Callable] = {
            SENSOR_DOMAIN: self._handle_no_action,
            NUMBER_DOMAIN: self._handle_number_button_action,
            INPUT_NUMBER_DOMAIN: self._handle_number_button_action,
            SWITCH_DOMAIN: self._handle_binary_action,
            INPUT_BOOLEAN_DOMAIN: self._handle_binary_action,
            BINARY_SENSOR_DOMAIN: self._handle_no_action,
            BUTTON_DOMAIN: self._handle_button_action,
            INPUT_BUTTON_DOMAIN: self._handle_button_action,
        }
        self._entity_wheel_action_map: dict[str, Callable] = {
            SENSOR_DOMAIN: self._handle_no_action,
            NUMBER_DOMAIN: self._handle_number_wheel_action,
            INPUT_NUMBER_DOMAIN: self._handle_number_wheel_action,
            SWITCH_DOMAIN: self._handle_no_action,
            INPUT_BOOLEAN_DOMAIN: self._handle_no_action,
            BINARY_SENSOR_DOMAIN: self._handle_no_action,
            BUTTON_DOMAIN: self._handle_no_action,
            INPUT_BUTTON_DOMAIN: self._handle_no_action,
        }

    def _get_button_from_id(self, button_id: str) -> Button | None:
        """Get Button from button_id."""
        if self._configuration is not None:
            for page in self._configuration.configuration.pages:
                for button in page.buttons:
                    if button.id == button_id:
                        return button
        return None

    def _update_configuration(
        self, button_id: str, button_state: ButtonState, button_value: int
    ) -> None:
        """Update Configuration with a button's current value."""
        if TYPE_CHECKING:
            assert self._configuration

        for page_idx, page in enumerate(self._configuration.configuration.pages):
            for button_idx, button in enumerate(page.buttons):
                if button.id == button_id:
                    self._configuration.configuration.pages[page_idx].buttons[
                        button_idx
                    ].state = button_state

                    self._configuration.configuration.pages[page_idx].buttons[
                        button_idx
                    ].value = button_value

        # TO DO: Evaluate when config_entry options should be updated
        # new_entry_data = dict(self._entry.options)
        # new_entry_data[CONF_HALO] = self._configuration.to_dict()

        # self.hass.config_entries.async_update_entry(self._entry, options=new_entry_data)

    def _translate_value(self, state: State) -> int:
        """Translate an input_value to a valid value for a Halo Button."""
        converted_state = int(float(state.state))

        # Do a map of values if necessary. Only works for Number entities
        if (
            {"min", "max"}.issubset(state.attributes)
            and state.attributes[ATTR_MIN] != 0
            and state.attributes[ATTR_MAX] != 100
        ):
            converted_state = int(
                np.interp(
                    converted_state,
                    [state.attributes[ATTR_MIN], state.attributes[ATTR_MAX]],
                    [MIN_VALUE, MAX_VALUE],
                )
            )

        # Fallback to a simple constrain to 0..100 for sensors
        elif converted_state < 0:
            converted_state = 0
        elif converted_state > 100:
            converted_state = 100

        return converted_state

    async def _update_entity_button_values(self, entity_id: str) -> None:
        """Send Halo Button configuration updates of current entity states."""
        # Get the button ids
        button_ids = []
        for mapped_button_id, mapped_entity_id in self._entity_map.items():
            if mapped_entity_id == entity_id:
                button_ids.append(mapped_button_id)

        # Handle update for pages that the entity is present on
        for button_id in button_ids:
            await self._handle_entity_update(entity_id, button_id)

    async def _handle_entity_state_change(
        self,
        event: Event[EventStateChangedData],
    ) -> None:
        """Handle state change of entities."""
        entity_id = event.data[CONF_ENTITY_ID]

        if entity_id not in self._entity_map.values():
            logging.error("Entity %s is not in entity map")
            return

        await self._update_entity_button_values(entity_id)

    # TO DO handle entity deletion
    # TO DO Get initial entity states

    async def _handle_entity_update(self, entity_id: str, button_id: str) -> None:
        """Handle state change events of entities."""

        entity_state = self.hass.states.get(entity_id)
        if entity_state is None:
            _LOGGER.error("Error retrieving state for %s", entity_id)
            return

        try:
            button_state, button_value = self._entity_update_map[entity_state.domain](
                entity_state
            )
        except KeyError:
            _LOGGER.error(
                "The Halo does not handle %s platform Button state updates yet",
                entity_state.domain,
            )
            return

        # Get button from Halo configuration
        if (button := self._get_button_from_id(button_id)) is None:
            _LOGGER.error("Unable to retrieve Halo button for %s", entity_id)
            return

        # Avoid unnecessary updates when Home Assistant is started if nothing has changed
        if button.state == button_state and button.value == button_value:
            _LOGGER.debug(
                "Skipping update for %s button on",
                button.title,
            )
            return

        # Update configuration
        self._update_configuration(button.id, button_state, button_value)

        # Send update to Halo
        await self._client.send(
            BaseUpdate(update=UpdateButton(button.id, button_state, button_value))
        )

    async def _handle_entity_button_action(self, button_id: str) -> None:
        """Handle actions of entities."""

        # Get entity_id
        try:
            entity_id = self._entity_map[button_id]
        except KeyError:
            _LOGGER.error(
                "Error associating button %s with an entity id. Entity map %s",
                button_id,
                self._entity_map,
            )
            return

        entity_state = self.hass.states.get(entity_id)
        if entity_state is None:
            _LOGGER.error("Error retrieving state for %s", entity_id)
            return

        try:
            await self._entity_button_action_map[entity_state.domain](
                entity_state, button_id
            )
        except KeyError:
            _LOGGER.error(
                "The Halo does not handle %s platform Button actions yet",
                entity_state.domain,
            )
            return

    async def _handle_entity_wheel_action(self, button_id: str, counts: int) -> None:
        """Handle actions of entities."""

        # Get entity_id
        try:
            entity_id = self._entity_map[button_id]
        except KeyError:
            _LOGGER.error(
                "Error associating button %s with an entity id. Entity map %s",
                button_id,
                self._entity_map,
            )
            return

        entity_state = self.hass.states.get(entity_id)
        if entity_state is None:
            _LOGGER.error("Error retrieving state for %s", entity_id)
            return

        try:
            await self._entity_wheel_action_map[entity_state.domain](
                entity_state, counts
            )
        except KeyError:
            _LOGGER.error(
                "The Halo does not handle %s platform Wheel actions yet",
                entity_state.domain,
            )
            return

    def _handle_number_update(self, state: State) -> tuple[ButtonState, int]:
        """Handle state change events of Number and Sensor entities."""
        try:
            # Currently assume that sensors have values from 0 to 100
            converted_state = self._translate_value(state)

        except ValueError:
            _LOGGER.error("Error when handling number / sensor state %s", state.state)

            button_state = ButtonState.INACTIVE
            button_value = 0

        else:
            # Process the on/off state for a number
            button_state = (
                ButtonState.ACTIVE if converted_state > 50 else ButtonState.INACTIVE
            )
            # Process the value state for a sensor
            button_value = converted_state

        return (button_state, button_value)

    async def _handle_number_button_action(
        self, entity_state: State, button_id: str
    ) -> None:
        """Handle Number Button entity actions."""
        if (button := self._get_button_from_id(button_id)) is None:
            _LOGGER.error(
                "Unable to retrieve Halo button for %s", entity_state.entity_id
            )
            return

        if button.state == ButtonState.ACTIVE:
            if "min" in entity_state.attributes:
                new_state = entity_state.attributes[ATTR_MIN]
            else:
                new_state = 0
        elif button.state == ButtonState.INACTIVE:
            if "max" in entity_state.attributes:
                new_state = entity_state.attributes[ATTR_MAX]
            else:
                new_state = 100

        _LOGGER.debug(
            "Sending %s to %s with value %s",
            SERVICE_SET_VALUE,
            entity_state.entity_id,
            new_state,
        )

        await self.hass.services.async_call(
            entity_state.domain,
            SERVICE_SET_VALUE,
            {
                ATTR_ENTITY_ID: entity_state.entity_id,
                ATTR_VALUE: new_state,
            },
        )

    async def _handle_number_wheel_action(
        self, entity_state: State, counts: int
    ) -> None:
        """Handle Number Button entity actions."""
        # button = self._get_button_from_id(button_id)

        # Add the step value
        if "step" in entity_state.attributes:
            new_state = float(entity_state.state) + (
                entity_state.attributes[ATTR_STEP] * counts
            )
        else:
            new_state = float(entity_state.state) + (1 * counts)

        _LOGGER.debug(
            "Sending %s to %s with value %s",
            SERVICE_SET_VALUE,
            entity_state.entity_id,
            new_state,
        )
        # Suppress any exceptions for now
        with contextlib.suppress(Invalid):
            await self.hass.services.async_call(
                entity_state.domain,
                SERVICE_SET_VALUE,
                {
                    ATTR_ENTITY_ID: entity_state.entity_id,
                    ATTR_VALUE: new_state,
                },
            )

    def _handle_binary_update(self, state: State) -> tuple[ButtonState, int]:
        """Handle state change events of Input Boolean, Switch and Binary Sensor entities."""

        # Process the on/off state for a input boolean switch / binary sensor
        try:
            button_state = (
                ButtonState.ACTIVE if state.state == STATE_ON else ButtonState.INACTIVE
            )
            button_value = 100 if state.state == STATE_ON else 0
        except ValueError:
            _LOGGER.exception("Error when handling switch state %s", state.state)

            button_state = ButtonState.INACTIVE
            button_value = 0

        return (button_state, button_value)

    async def _handle_binary_action(self, entity_state: State, _: str) -> None:
        """Handle Input Boolean and switch Button entity actions."""
        _LOGGER.debug("Sending %s to %s", SERVICE_SET_VALUE, entity_state.entity_id)

        await self.hass.services.async_call(
            entity_state.domain,
            SERVICE_TOGGLE,
            {ATTR_ENTITY_ID: entity_state.entity_id},
        )

    def _handle_button_update(self, _: State) -> tuple[ButtonState, int]:
        """Handle state change events of Input Button and Button entities."""
        # Currently do nothing when a button has been pressed.
        # Ideally there would be some indication, but it is cumbersome for now.
        return (ButtonState.INACTIVE, 0)

    async def _handle_button_action(self, entity_state: State, _: str) -> None:
        """Handle Button Button entity actions."""
        _LOGGER.debug("Sending %s to %s", SERVICE_PRESS, entity_state.entity_id)

        await self.hass.services.async_call(
            entity_state.domain,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: entity_state.entity_id},
        )

    async def _handle_no_action(self, entity_state: State, counts: str) -> None:
        """Handle Button entity with no actions."""
        _LOGGER.debug("No action available for %s", entity_state.entity_id)

    def _update_connection_status(self) -> None:
        """Update all entities of the connection status."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{CONNECTION_STATUS}",
            self._client.websocket_connected,
        )

    async def on_connection(self) -> None:
        """Handle WebSocket connection made."""
        _LOGGER.debug("Connected to the %s event channel", self.entry.title)

        if self._configuration:
            # Send initial configuration
            await self._client.send(self._configuration)

            # Send entity states as updates
            for entity_id in self._entity_map.values():
                # print(entity_id)
                await self._update_entity_button_values(entity_id)
        else:
            _LOGGER.debug(
                "Add a configuration for Home Assistant entities to %s in config flow options",
                self.entry.title,
            )

        self._update_connection_status()

    def on_connection_lost(self) -> None:
        """Handle WebSocket connection lost."""
        _LOGGER.error("Lost connection to the %s", self.entry.title)
        self._update_connection_status()

    async def on_button_event(self, event: HaloButtonEvent) -> None:
        """Send halo_button dispatch."""
        if event.state == ButtonEventState.RELEASED:
            await self._handle_entity_button_action(event.id)

    def on_power_event(self, event: PowerEvent) -> None:
        """Send halo_power dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.HALO_POWER}",
            event,
        )

    def on_status_event(self, event: StatusEvent) -> None:
        """Send halo_status dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.HALO_STATUS}",
            event,
        )

    def on_system_event(self, event: SystemEvent) -> None:
        """Send halo_system dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.HALO_SYSTEM}",
            event,
        )

    async def on_wheel_event(self, event: WheelEvent) -> None:
        """Send halo_wheel dispatch."""

        await self._handle_entity_wheel_action(event.id, event.counts)

    def on_all_events_raw(self, event: HaloBaseWebSocketResponse) -> None:
        """Receive all events."""
        debug_event = {
            "device_id": self._device.id,
            "serial_number": int(self._unique_id),
            **event,
        }

        _LOGGER.debug("%s", debug_event)
        self.hass.bus.async_fire(HALO_WEBSOCKET_EVENT, debug_event)


class MozartWebsocket(MozartBase):
    """The WebSocket listener(s)."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: MozartClient,
    ) -> None:
        """Initialize the entity coordinator."""
        super().__init__(config_entry, client)

        self.hass = hass
        self._device = self.get_device(hass, self._unique_id)

        if TYPE_CHECKING:
            assert isinstance(self._client, MozartClient)

        # WebSocket callbacks
        self._client.get_active_listening_mode_notifications(
            self.on_active_listening_mode
        )
        self._client.get_active_speaker_group_notifications(
            self.on_active_speaker_group
        )
        self._client.get_battery_notifications(self.on_battery_notification)
        self._client.get_beo_remote_button_notifications(
            self.on_beo_remote_button_notification
        )
        self._client.get_button_notifications(self.on_button_notification)
        self._client.get_notification_notifications(self.on_notification_notification)
        self._client.get_on_connection_lost(self.on_connection_lost)
        self._client.get_on_connection(self.on_connection)
        self._client.get_playback_error_notifications(
            self.on_playback_error_notification
        )
        self._client.get_playback_metadata_notifications(
            self.on_playback_metadata_notification
        )
        self._client.get_playback_progress_notifications(
            self.on_playback_progress_notification
        )
        self._client.get_playback_source_notifications(
            self.on_playback_source_notification
        )
        self._client.get_playback_state_notifications(
            self.on_playback_state_notification
        )
        self._client.get_software_update_state_notifications(
            self.on_software_update_state
        )
        self._client.get_source_change_notifications(self.on_source_change_notification)
        self._client.get_volume_notifications(self.on_volume_notification)

        # Used for firing events and debugging
        self._client.get_all_notifications_raw(self.on_all_notifications_raw)

    def _update_connection_status(self) -> None:
        """Update all entities of the connection status."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{CONNECTION_STATUS}",
            self._client.websocket_connected,
        )

    def on_connection(self) -> None:
        """Handle WebSocket connection made."""
        _LOGGER.debug("Connected to the %s notification channel", self.entry.title)
        self._update_connection_status()

    def on_connection_lost(self) -> None:
        """Handle WebSocket connection lost."""
        _LOGGER.error("Lost connection to the %s", self.entry.title)
        self._update_connection_status()

    def on_active_listening_mode(self, notification: ListeningModeProps) -> None:
        """Send active_listening_mode dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.ACTIVE_LISTENING_MODE}",
            notification,
        )

    def on_active_speaker_group(self, notification: SpeakerGroupOverview) -> None:
        """Send active_speaker_group dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.ACTIVE_SPEAKER_GROUP}",
            notification,
        )

    def on_battery_notification(self, notification: BatteryState) -> None:
        """Send battery dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.BATTERY}",
            notification,
        )

    def on_beo_remote_button_notification(self, notification: BeoRemoteButton) -> None:
        """Send beo_remote_button dispatch."""
        if TYPE_CHECKING:
            assert notification.type

        # Send to event entity
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.BEO_REMOTE_BUTTON}_{notification.key}",
            EVENT_TRANSLATION_MAP[notification.type],
        )

    def on_button_notification(self, notification: ButtonEvent) -> None:
        """Send button dispatch."""
        assert notification.state
        # Send to event entity
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.BUTTON}_{notification.button}",
            EVENT_TRANSLATION_MAP[notification.state],
        )

    async def on_notification_notification(
        self, notification: WebsocketNotificationTag
    ) -> None:
        """Send notification dispatch."""
        assert notification.value

        # Try to match the notification type with available WebsocketNotification members
        notification_type = try_parse_enum(WebsocketNotification, notification.value)

        if notification_type in (
            WebsocketNotification.BEOLINK_PEERS,
            WebsocketNotification.BEOLINK_LISTENERS,
            WebsocketNotification.BEOLINK_AVAILABLE_LISTENERS,
        ):
            async_dispatcher_send(
                self.hass,
                f"{self._unique_id}_{WebsocketNotification.BEOLINK}",
            )
        elif notification_type is WebsocketNotification.CONFIGURATION:
            async_dispatcher_send(
                self.hass,
                f"{self._unique_id}_{WebsocketNotification.CONFIGURATION}",
            )
        elif notification_type in (
            WebsocketNotification.PROXIMITY_PRESENCE_DETECTED,
            WebsocketNotification.PROXIMITY_PRESENCE_NOT_DETECTED,
        ):
            async_dispatcher_send(
                self.hass,
                f"{self._unique_id}_{WebsocketNotification.PROXIMITY}",
                EVENT_TRANSLATION_MAP[notification.value],
            )
        # This notification is triggered by a remote pairing, unpairing and connecting to a device
        # So the current remote devices have to be compared to available remotes to determine action
        elif notification_type is WebsocketNotification.REMOTE_CONTROL_DEVICES:
            device_registry = dr.async_get(self.hass)
            device_serial_numbers = [
                device.serial_number
                for device in device_registry.devices.get_devices_for_config_entry_id(
                    self.entry.entry_id
                )
                if device.serial_number is not None
                and device.model == BangOlufsenModel.BEOREMOTE_ONE
            ]
            remote_serial_numbers = [
                remote.serial_number
                for remote in await get_remotes(self._client)
                if remote.serial_number is not None
            ]
            # Check if number of remote devices correspond to number of paired remotes
            if len(remote_serial_numbers) != len(device_serial_numbers):
                # Reinitialize the config entry to update Beoremote One entities and device
                # Wait 5 seconds for the remote to be properly available to the device
                _LOGGER.info(
                    "A Beoremote One has been paired or unpaired to %s. Reloading config entry to add device",
                    self._device.name,
                )
                self.hass.loop.call_later(
                    5,
                    self.hass.config_entries.async_schedule_reload,
                    self.entry.entry_id,
                )

        elif notification_type is WebsocketNotification.REMOTE_MENU_CHANGED:
            async_dispatcher_send(
                self.hass,
                f"{self._unique_id}_{WebsocketNotification.REMOTE_MENU_CHANGED}",
            )

    def on_playback_error_notification(self, notification: PlaybackError) -> None:
        """Send playback_error dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.PLAYBACK_ERROR}",
            notification,
        )

    def on_playback_metadata_notification(
        self, notification: PlaybackContentMetadata
    ) -> None:
        """Send playback_metadata dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.PLAYBACK_METADATA}",
            notification,
        )

    def on_playback_progress_notification(self, notification: PlaybackProgress) -> None:
        """Send playback_progress dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.PLAYBACK_PROGRESS}",
            notification,
        )

    def on_playback_source_notification(self, notification: Source) -> None:
        """Send playback_source dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.PLAYBACK_SOURCE}",
            notification,
        )

    def on_playback_state_notification(self, notification: RenderingState) -> None:
        """Send playback_state dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.PLAYBACK_STATE}",
            notification,
        )

    def on_source_change_notification(self, notification: Source) -> None:
        """Send source_change dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.SOURCE_CHANGE}",
            notification,
        )

    def on_volume_notification(self, notification: VolumeState) -> None:
        """Send volume dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WebsocketNotification.VOLUME}",
            notification,
        )

    async def on_software_update_state(self, _: SoftwareUpdateState) -> None:
        """Check device sw version."""
        software_status = await self._client.get_softwareupdate_status()

        # Update the HA device if the sw version does not match
        if software_status.software_version != self._device.sw_version:
            device_registry = dr.async_get(self.hass)

            device_registry.async_update_device(
                device_id=self._device.id,
                sw_version=software_status.software_version,
            )

    def on_all_notifications_raw(self, notification: BaseWebSocketResponse) -> None:
        """Receive all notifications."""

        _LOGGER.debug("%s", notification)
        self.hass.bus.async_fire(
            MOZART_WEBSOCKET_EVENT,
            {
                "device_id": self._device.id,
                "serial_number": int(self._unique_id),
                **notification,
            },
        )
