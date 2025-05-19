"""WebSocket listener(s) for the Bang & Olufsen integration."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
import contextlib
from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING, Any, TypedDict

from mozart_api.models import (
    BatteryState,
    BeoRemoteButton,
    ButtonEvent as MozartButtonEvent,
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
from mozart_api.mozart_client import (
    BaseWebSocketResponse as MozartBaseWebSocketResponse,
    MozartClient,
)
import numpy as np
from voluptuous import Invalid

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_CURRENT_TILT_POSITION,
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    DOMAIN as COVER_DOMAIN,
    SERVICE_SET_COVER_POSITION,
    SERVICE_SET_COVER_TILT_POSITION,
    SERVICE_TOGGLE_COVER_TILT,
    CoverEntityFeature,
    CoverState,
)
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN
from homeassistant.components.input_button import DOMAIN as INPUT_BUTTON_DOMAIN
from homeassistant.components.input_number import DOMAIN as INPUT_NUMBER_DOMAIN
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_BRIGHTNESS_STEP_PCT,
    DOMAIN as LIGHT_DOMAIN,
)
from homeassistant.components.number import (
    ATTR_MAX,
    ATTR_MIN,
    ATTR_STEP,
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.components.scene import DOMAIN as SCENE_DOMAIN
from homeassistant.components.script import DOMAIN as SCRIPT_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    CONF_ENTITY_ID,
    CONF_ID,
    CONF_STATE,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util.enum import try_parse_enum

from .beoremote_halo.const import MAX_VALUE, MIN_VALUE
from .beoremote_halo.halo import Halo
from .beoremote_halo.helpers import get_button_from_id
from .beoremote_halo.models import (
    BaseWebSocketResponse as HaloBaseWebSocketResponse,
    ButtonEvent as HaloButtonEvent,
    ButtonEventState,
    ButtonState,
    Icon,
    PowerEvent,
    StatusEvent,
    SystemEvent,
    Text,
    Update,
    UpdateButton,
    WheelEvent,
)
from .beoremote_halo.util import (
    clamp_button_value,
    interpolate_button_value,
    trim_button_text,
)
from .const import (
    CONF_CONTENT,
    CONF_ENTITY_MAP,
    CONF_VALUE,
    CONNECTION_STATUS,
    EVENT_TRANSLATION_MAP,
    HALO_WEBSOCKET_EVENT,
    HALO_WHEEL_TIMEOUT,
    MOZART_WEBSOCKET_EVENT,
    BangOlufsenModel,
    EntityMapValues,
    WebsocketNotification,
)
from .entity import HaloBase, MozartBase
from .util import get_remotes

_LOGGER = logging.getLogger(__name__)


@dataclass
class WheelTaskHandler:
    """Store Task, Timer and counter for wheel event service calls."""

    task: asyncio.Task | None = None
    timer: asyncio.TimerHandle | None = None
    content: Text | Icon | None = None
    counter: int = 0


class UpdateButtonKwargs(TypedDict, total=False):
    """kwargs for the UpdateButton class."""

    id: str
    state: ButtonState
    value: int
    title: str
    subtitle: str
    content: Text


class HaloWebsocket(HaloBase):
    """WebSocket for Halo."""

    _entity_map: dict[str, EntityMapValues] = {}
    _entity_ids: list[str] = []
    _wheel_action_handlers: dict[str, WheelTaskHandler] = {}

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
            self._entity_ids = [
                entity_settings[CONF_ENTITY_ID]
                for entity_settings in self._entity_map.values()
            ]

            async_track_state_change_event(
                self.hass,
                self._entity_ids,
                self._manage_entity_state_change,
            )
            # Create wheel counters
            self._wheel_action_handlers = {
                entity_id: WheelTaskHandler() for entity_id in self._entity_ids
            }

        # Dict for associating platforms with update methods
        self._entity_update_map: dict[
            str, Callable[[State], tuple[ButtonState, int]]
        ] = {
            BINARY_SENSOR_DOMAIN: self._handle_binary_update,
            BUTTON_DOMAIN: self._handle_no_update,
            COVER_DOMAIN: self._handle_cover_update,
            INPUT_BOOLEAN_DOMAIN: self._handle_binary_update,
            INPUT_BUTTON_DOMAIN: self._handle_no_update,
            INPUT_NUMBER_DOMAIN: self._handle_number_update,
            LIGHT_DOMAIN: self._handle_light_update,
            NUMBER_DOMAIN: self._handle_number_update,
            SCENE_DOMAIN: self._handle_no_update,
            SCRIPT_DOMAIN: self._handle_no_update,
            SENSOR_DOMAIN: self._handle_number_update,
            SWITCH_DOMAIN: self._handle_binary_update,
        }

        # Dict for associating platforms with button methods
        self._entity_action_map: dict[
            str, Callable[[State, str], Coroutine[Any, Any, None]]
        ] = {
            BINARY_SENSOR_DOMAIN: self._handle_no_action,
            BUTTON_DOMAIN: self._handle_button_action,
            COVER_DOMAIN: self._handle_cover_action,
            INPUT_BOOLEAN_DOMAIN: self._handle_binary_action,
            INPUT_BUTTON_DOMAIN: self._handle_button_action,
            INPUT_NUMBER_DOMAIN: self._handle_number_action,
            LIGHT_DOMAIN: self._handle_binary_action,
            NUMBER_DOMAIN: self._handle_number_action,
            SCENE_DOMAIN: self._handle_scene_action,
            SCRIPT_DOMAIN: self._handle_script_action,
            SENSOR_DOMAIN: self._handle_no_action,
            SWITCH_DOMAIN: self._handle_binary_action,
        }

        # Dict for associating platforms with wheel action calculation methods
        self._entity_wheel_calculation_map: dict[
            str, Callable[[State], tuple[str, str, dict[str, Any]] | None]
        ] = {
            BINARY_SENSOR_DOMAIN: self._calculate_no_wheel_action,
            BUTTON_DOMAIN: self._calculate_no_wheel_action,
            COVER_DOMAIN: self._calculate_cover_wheel_action,
            INPUT_BOOLEAN_DOMAIN: self._calculate_binary_wheel_action,
            INPUT_BUTTON_DOMAIN: self._calculate_no_wheel_action,
            INPUT_NUMBER_DOMAIN: self._calculate_number_wheel_value,
            LIGHT_DOMAIN: self._calculate_light_wheel_action,
            NUMBER_DOMAIN: self._calculate_number_wheel_value,
            SCENE_DOMAIN: self._calculate_no_wheel_action,
            SCRIPT_DOMAIN: self._calculate_no_wheel_action,
            SENSOR_DOMAIN: self._calculate_no_wheel_action,
            SWITCH_DOMAIN: self._calculate_binary_wheel_action,
        }

    def _get_entity_state_from_id(self, button_id: str) -> State | None:
        """Get entity state and handle invalid entities."""
        entity_id = self._entity_map[button_id][CONF_ENTITY_ID]

        entity_state = self.hass.states.get(entity_id)
        if entity_state is None:
            _LOGGER.error("Error retrieving state for %s", entity_id)
            return None

        return entity_state

    # Button update methods
    async def _manage_entity_state_change(
        self,
        event: Event[EventStateChangedData],
    ) -> None:
        """Manage state change of an entity."""
        # TO DO handle entity deletion
        await self._manage_entity_updates(event.data[CONF_ENTITY_ID])

    async def _manage_entity_updates(self, entity_id: str) -> None:
        """Send Halo Button configuration updates of current entity states."""
        # Get the button ids
        button_ids = []
        for mapped_button_id, mapped_entity_settings in self._entity_map.items():
            if mapped_entity_settings[CONF_ENTITY_ID] == entity_id:
                button_ids.append(mapped_button_id)

        # Handle update for pages that the entity is present on
        for button_id in button_ids:
            await self._manage_entity_update(entity_id, button_id)

    async def _manage_entity_update(self, entity_id: str, button_id: str) -> None:
        """Manage state change events of entities."""

        # Determine if the entity state should be used as content
        use_state = self._entity_map[button_id][CONF_STATE]

        entity_state = self.hass.states.get(entity_id)
        if entity_state is None:
            _LOGGER.debug("Error retrieving state for %s", entity_id)
            return

        button_state, button_value = self._entity_update_map[entity_state.domain](
            entity_state
        )
        # Create content that will be used if the "state" setting is enabled for the button
        content = Text(trim_button_text(str(entity_state.state)))

        # Get button from Halo configuration
        try:
            button = get_button_from_id(self._client.configuration, button_id)
        except ValueError:
            _LOGGER.debug("Error retrieving button %s from configuration", button_id)
            return

        # Avoid unnecessary updates when Home Assistant is started if nothing has changed
        if button.state == button_state and button.value == button_value:
            # Check button content if the entity state is used
            if use_state is True and button.content != content:
                pass
            else:
                _LOGGER.debug("Skipping update for %s button", button.title)
                return

        update_kwargs: UpdateButtonKwargs = {
            CONF_ID: button.id,
            CONF_STATE: button_state,
            CONF_VALUE: button_value,
        }

        # Add entity value as content update if defined
        if use_state is True:
            update_kwargs[CONF_CONTENT] = content

        # Send update to Halo
        await self._client.update(Update(update=UpdateButton(**update_kwargs)))

    def _handle_binary_update(self, state: State) -> tuple[ButtonState, int]:
        """Handle state change events of entities that provide a binary 'on' or 'off' as state."""

        # Process the on/off state for a input boolean switch / binary sensor
        try:
            button_state = (
                ButtonState.ACTIVE if state.state == STATE_ON else ButtonState.INACTIVE
            )
            button_value = 100 if state.state == STATE_ON else 0
        except ValueError:
            _LOGGER.debug("Error when handling switch or binary_sensor state %s", state)

            button_state = ButtonState.INACTIVE
            button_value = 0

        return (button_state, button_value)

    def _handle_cover_update(self, state: State) -> tuple[ButtonState, int]:
        """Handle state change events of Cover entities."""

        # Process the state for a cover
        try:
            button_state = (
                ButtonState.ACTIVE
                if state.state == CoverState.CLOSED
                else ButtonState.INACTIVE
            )
            # Try to use position
            if ATTR_CURRENT_POSITION in state.attributes:
                button_value = state.attributes[ATTR_CURRENT_POSITION]
            elif ATTR_CURRENT_TILT_POSITION in state.attributes:
                button_value = state.attributes[ATTR_CURRENT_TILT_POSITION]
            # Fallback to state value
            else:
                button_value = 100 if state.state == CoverState.CLOSED else 0

        except ValueError:
            _LOGGER.debug("Error when handling cover state %s", state)

            button_state = ButtonState.INACTIVE
            button_value = 0

        return (button_state, button_value)

    def _handle_light_update(self, state: State) -> tuple[ButtonState, int]:
        """Handle state change events of Light entities."""
        try:
            # Determine value based on available attributes
            if ATTR_BRIGHTNESS in state.attributes:
                brightness = (
                    state.attributes[ATTR_BRIGHTNESS]
                    if state.attributes[ATTR_BRIGHTNESS] is not None
                    else 0
                )
                converted_state = interpolate_button_value(brightness, 1, 255)

            else:
                converted_state = MAX_VALUE if state.state == STATE_ON else MIN_VALUE

        except ValueError:
            _LOGGER.debug("Error when handling light state %s", state)

            button_state = ButtonState.INACTIVE
            button_value = 0

        else:
            # Process the on/off state for a light
            button_state = (
                ButtonState.ACTIVE if state.state == STATE_ON else ButtonState.INACTIVE
            )
            # Process the value state for a light
            button_value = converted_state

        return (button_state, button_value)

    def _handle_no_update(self, _: State) -> tuple[ButtonState, int]:
        """Handle entities that provide no useful state."""
        # Currently do nothing when a button has been pressed.
        # Ideally there would be some indication, but it is cumbersome for now.
        return (ButtonState.INACTIVE, 0)

    def _handle_number_update(self, state: State) -> tuple[ButtonState, int]:
        """Handle state change events of entities that provide a number as state."""
        try:
            converted_state = int(float(state.state))
            if (
                {"min", "max"}.issubset(state.attributes)
                and state.attributes[ATTR_MIN] != 0
                and state.attributes[ATTR_MAX] != 100
            ):
                converted_state = interpolate_button_value(
                    converted_state,
                    state.attributes[ATTR_MIN],
                    state.attributes[ATTR_MAX],
                )
            else:
                converted_state = clamp_button_value(converted_state)

        except ValueError:
            _LOGGER.debug("Error when handling number or sensor state %s", state)

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

    # Button action methods
    async def _manage_entity_action(self, button_id: str) -> None:
        """Manage actions of entities."""

        if (entity_state := self._get_entity_state_from_id(button_id)) is None:
            return

        await self._entity_action_map[entity_state.domain](entity_state, button_id)

    async def _handle_binary_action(self, entity_state: State, button_id: str) -> None:
        """Handle binary entity actions."""
        _LOGGER.debug("Sending %s to %s", SERVICE_TOGGLE, entity_state.entity_id)

        await self.hass.services.async_call(
            entity_state.domain,
            SERVICE_TOGGLE,
            {ATTR_ENTITY_ID: entity_state.entity_id},
        )

    async def _handle_button_action(self, entity_state: State, button_id: str) -> None:
        """Handle Button entity button actions."""
        _LOGGER.debug("Sending %s to %s", SERVICE_PRESS, entity_state.entity_id)

        await self.hass.services.async_call(
            entity_state.domain,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: entity_state.entity_id},
        )

    async def _handle_cover_action(self, entity_state: State, button_id: str) -> None:
        """Handle Cover entity button actions."""
        # Covers may support either toggle, toggle tilt or both.
        # Currently tilt is used only if toggle is not available
        action = SERVICE_TOGGLE
        if entity_state.attributes[ATTR_SUPPORTED_FEATURES] & CoverEntityFeature.OPEN:
            pass
        elif (
            entity_state.attributes[ATTR_SUPPORTED_FEATURES]
            & CoverEntityFeature.OPEN_TILT
        ):
            action = SERVICE_TOGGLE_COVER_TILT

        _LOGGER.debug("Sending %s to %s", action, entity_state.entity_id)

        await self.hass.services.async_call(
            entity_state.domain,
            action,
            {ATTR_ENTITY_ID: entity_state.entity_id},
        )

    async def _handle_no_action(self, entity_state: State, button_id: str) -> None:
        """Handle entity with no associated button action."""
        _LOGGER.debug("No button action available for %s", entity_state.entity_id)

    async def _handle_number_action(self, entity_state: State, button_id: str) -> None:
        """Handle Number Button entity button actions."""

        button = get_button_from_id(self._client.configuration, button_id)

        if button.state == ButtonState.ACTIVE:
            if "min" in entity_state.attributes:
                new_state = entity_state.attributes[ATTR_MIN]
            else:
                new_state = MIN_VALUE
        elif button.state == ButtonState.INACTIVE:
            if "max" in entity_state.attributes:
                new_state = entity_state.attributes[ATTR_MAX]
            else:
                new_state = MAX_VALUE

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

    async def _handle_scene_action(self, entity_state: State, button_id: str) -> None:
        """Handle Scene entity button actions."""
        _LOGGER.debug("Sending %s to %s", SERVICE_TURN_ON, entity_state.entity_id)

        await self.hass.services.async_call(
            entity_state.domain,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: entity_state.entity_id},
        )

    async def _handle_script_action(self, entity_state: State, button_id: str) -> None:
        """Handle Script entity button actions."""
        _LOGGER.debug("Activating script: %s ", entity_state.name)

        await self.hass.services.async_call(entity_state.domain, entity_state.name)

    # Button wheel calculation methods
    def _calculate_binary_wheel_action(
        self, entity_state: State
    ) -> tuple[str, str, dict[str, Any]] | None:
        """Calculate Switch entity wheel value and return action variables."""

        # Ensure valid and not-useless action value
        if (
            entity_state.state == STATE_ON
            and self._wheel_action_handlers[entity_state.entity_id].counter <= -2
        ):
            action = SERVICE_TURN_OFF
        elif (
            entity_state.state == STATE_OFF
            and self._wheel_action_handlers[entity_state.entity_id].counter >= 2
        ):
            action = SERVICE_TURN_ON
        else:
            return None

        return (
            STATE_ON if entity_state.state == STATE_OFF else STATE_OFF,
            action,
            {},
        )

    def _calculate_cover_wheel_action(
        self, entity_state: State
    ) -> tuple[str, str, dict[str, Any]] | None:
        """Calculate Cover entity wheel value and return action variables."""

        # Determine service based on attributes
        if ATTR_CURRENT_POSITION in entity_state.attributes:
            state_attribute = ATTR_CURRENT_POSITION
            action = SERVICE_SET_COVER_POSITION
            action_attribute = ATTR_POSITION
        elif ATTR_CURRENT_TILT_POSITION in entity_state.attributes:
            state_attribute = ATTR_CURRENT_TILT_POSITION
            action = SERVICE_SET_COVER_TILT_POSITION
            action_attribute = ATTR_TILT_POSITION
        else:
            _LOGGER.debug(
                "Unable to determine cover action for %s", entity_state.entity_id
            )
            return None

        # Clamp the value.
        new_position = int(
            np.clip(
                entity_state.attributes[state_attribute]
                + self._wheel_action_handlers[entity_state.entity_id].counter,
                0,
                100,
            )
        )

        # Avoid sending service calls if they do not change the entity state
        if int(float(entity_state.attributes[state_attribute])) == new_position:
            return None

        return (
            str(new_position),
            action,
            {action_attribute: new_position},
        )

    def _calculate_light_wheel_action(
        self, entity_state: State
    ) -> tuple[str, str, dict[str, Any]] | None:
        """Calculate Light entity wheel value and return action variables."""

        # Ensure valid and not-useless action value
        brightness_step = int(
            np.clip(
                self._wheel_action_handlers[entity_state.entity_id].counter, -100, 100
            )
        )

        if (
            # No change in percentage
            brightness_step == 0
            # Negative step while state is STATE_OFF
            or (entity_state.state == STATE_OFF and brightness_step < 0)
            # Maximum brightness already reached
            or (
                ATTR_BRIGHTNESS in entity_state.attributes
                and entity_state.attributes[ATTR_BRIGHTNESS] == 255
                and brightness_step > 0
            )
        ):
            return None

        return (
            f"{brightness_step}%",
            SERVICE_TURN_ON,
            {ATTR_BRIGHTNESS_STEP_PCT: brightness_step},
        )

    def _calculate_no_wheel_action(self, entity_state: State) -> None:
        """Handle entity with no associated wheel action."""
        _LOGGER.debug("No wheel action available for %s", entity_state.entity_id)

    def _calculate_number_wheel_value(
        self, entity_state: State
    ) -> tuple[str, str, dict[str, Any]] | None:
        """Calculate Number entity wheel value and return action variables."""

        # Add the step value
        if "step" in entity_state.attributes:
            new_number = float(entity_state.state) + (
                entity_state.attributes[ATTR_STEP]
                * self._wheel_action_handlers[entity_state.entity_id].counter
            )
        else:
            new_number = float(entity_state.state) + (
                1 * self._wheel_action_handlers[entity_state.entity_id].counter
            )

        # Clamp the value if possible
        if {"min", "max"}.issubset(entity_state.attributes):
            new_number = np.clip(
                new_number,
                entity_state.attributes[ATTR_MIN],
                entity_state.attributes[ATTR_MAX],
            )

        # Avoid sending service calls if they do not change the entity state
        if int(float(entity_state.state)) == new_number:
            return None

        return (
            str(new_number),
            SERVICE_SET_VALUE,
            {ATTR_VALUE: new_number},
        )

    # Button wheel action tasks
    async def _manage_entity_wheel_action_tasks(
        self, button_id: str, counts: int
    ) -> None:
        """Handle wheel actions of entities."""

        if (entity_state := self._get_entity_state_from_id(button_id)) is None:
            return

        # Increment or decrement counter
        self._wheel_action_handlers[entity_state.entity_id].counter += counts

        # Calculate new entity value
        if (
            data := self._entity_wheel_calculation_map[entity_state.domain](
                entity_state
            )
        ) is None:
            _LOGGER.debug("Skipping wheel action task")
            # Reset counter
            self._wheel_action_handlers[entity_state.entity_id].counter = 0
            return

        preview_value, action, action_data = data

        # Show preview of new value
        await self._preview_wheel_action(preview_value, button_id, entity_state)

        # Cancel any scheduled action calls
        if (
            timer := self._wheel_action_handlers[entity_state.entity_id].timer
        ) is not None:
            timer.cancel()

        # Schedule a new action call
        self._wheel_action_handlers[
            entity_state.entity_id
        ].timer = self.hass.loop.call_later(
            HALO_WHEEL_TIMEOUT,
            self._create_wheel_action_task,
            button_id,
            entity_state,
            action,
            action_data,
        )

    async def _preview_wheel_action(
        self,
        preview_value: str,
        button_id: str,
        entity_state: State,
    ) -> None:
        """Show wheel action preview."""
        # Save original content if needed
        if (
            self._entity_map[button_id][CONF_STATE] is False
            and self._wheel_action_handlers[entity_state.entity_id].content is None
        ):
            self._wheel_action_handlers[
                entity_state.entity_id
            ].content = get_button_from_id(
                self._client.configuration, button_id
            ).content

        # Show preview of value
        _ = await self._client.update(
            Update(UpdateButton(button_id, content=Text(preview_value))),
        )

    def _create_wheel_action_task(
        self,
        button_id: str,
        entity_state: State,
        action: str,
        action_data: dict[str, Any] | None = None,
    ) -> None:
        """Create wheel action task."""

        # Wrap action call in a task as callbacks can't be async
        self._wheel_action_handlers[entity_state.entity_id].task = asyncio.create_task(
            self._handle_wheel_action_task(button_id, entity_state, action, action_data)
        )

    async def _handle_wheel_action_task(
        self,
        button_id: str,
        entity_state: State,
        action: str,
        action_data: dict[str, Any] | None = None,
    ) -> None:
        """Execute wheel action call."""
        if action_data is None:
            action_data = {}

        _LOGGER.debug(
            "Sending %s to %s with service data: %s",
            action,
            entity_state.entity_id,
            action_data,
        )
        # Suppress any exceptions for now
        with contextlib.suppress(Invalid):
            await self.hass.services.async_call(
                entity_state.domain,
                action,
                {ATTR_ENTITY_ID: entity_state.entity_id, **action_data},
            )

        # Reset counter, timer and content
        self._wheel_action_handlers[entity_state.entity_id].counter = 0
        self._wheel_action_handlers[entity_state.entity_id].timer = None
        # Reset button content to original content from configuration
        if (
            self._entity_map[button_id][CONF_STATE] is False
            and self._wheel_action_handlers[entity_state.entity_id].content is not None
        ):
            await self._client.update(
                Update(
                    UpdateButton(
                        button_id,
                        content=self._wheel_action_handlers[
                            entity_state.entity_id
                        ].content,
                    )
                )
            )

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

        if self._client.configuration:
            # Send entity states as updates
            for entity_id in self._entity_ids:
                await self._manage_entity_updates(entity_id)

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
            await self._manage_entity_action(event.id)

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
            event.state,
        )

    async def on_wheel_event(self, event: WheelEvent) -> None:
        """Send halo_wheel dispatch."""

        await self._manage_entity_wheel_action_tasks(event.id, event.counts)

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

    def on_button_notification(self, notification: MozartButtonEvent) -> None:
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
                _LOGGER.info(
                    "A Beoremote One has been paired or unpaired to %s. Reloading config entry to add device and entities",
                    self._device.name,
                )
                self.hass.config_entries.async_schedule_reload(self.entry.entry_id)

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

    def on_all_notifications_raw(
        self, notification: MozartBaseWebSocketResponse
    ) -> None:
        """Receive all notifications."""
        debug_notification = {
            "device_id": self._device.id,
            "serial_number": int(self._unique_id),
            **notification,
        }

        _LOGGER.debug("%s", debug_notification)
        self.hass.bus.async_fire(MOZART_WEBSOCKET_EVENT, debug_notification)
