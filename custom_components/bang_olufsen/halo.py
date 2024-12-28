"""Halo client."""

import asyncio
from asyncio import (  # type: ignore[attr-defined]
    Queue,
    QueueEmpty,
    QueueFull,
    QueueShutDown,
)
from collections import defaultdict
from collections.abc import Awaitable, Callable
import contextlib
from dataclasses import dataclass
from enum import StrEnum
import json
import logging
from typing import Final, Literal, TypedDict, cast
from uuid import uuid1

from aiohttp import ClientSession, ClientTimeout, WSMessageTypeError
from aiohttp.client_exceptions import (
    ClientConnectorError,
    ClientOSError,
    ServerTimeoutError,
)
from inflection import underscore
from mashumaro.mixins.json import DataClassJSONMixin

WEBSOCKET_TIMEOUT = 5.0

logger = logging.getLogger(__name__)

MIN_VALUE: Final = 0
MAX_VALUE: Final = 100


# TO DO: Add serialization aliases to id


class Icons(StrEnum):
    """Available icons for buttons."""

    ALARM = "alarm"
    ALTERNATIVE = "alternative"
    ARM_AWAY = "arm_away"
    ARM_STAY = "arm_stay"
    AUTO = "auto"
    BATH_TUB = "bath_tub"
    BLINDS = "blinds"
    BLISS = "bliss"
    BUTLER = "butler"
    CINEMA = "cinema"
    CLEAN = "clean"
    CLOCK = "clock"
    COFFEE = "coffee"
    COOL = "cool"
    CREATIVE = "creative"
    CURTAINS = "curtains"
    DINNER = "dinner"
    DISARM = "disarm"
    DOOR = "door"
    DOORLOCK = "doorlock"
    ENERGIZE = "energize"
    ENJOY = "enjoy"
    ENTERTAIN = "entertain"
    FAN = "fan"
    FIREPLACE = "fireplace"
    FORCED_ARM = "forced_arm"
    GAMING = "gaming"
    GARAGE = "garage"
    GATE = "gate"
    GOOD_MORNING = "good_morning"
    GOOD_NIGHT = "good_night"
    HEAT = "heat"
    HUMIDITY = "humidity"
    INDULGE = "indulge"
    LEAVING = "leaving"
    LIGHTS = "lights"
    LOCK = "lock"
    MEETING = "meeting"
    MOVIE = "movie"
    MUSIC = "music"
    NOTIFICATION = "notification"
    OFF = "off"
    PARTY = "party"
    POOL = "pool"
    PRIVACY = "privacy"
    PRODUCTIVE = "productive"
    READING = "reading"
    RELAX = "relax"
    REQUEST_CAR = "request_car"
    RGB_LIGHTS = "rgb_lights"
    ROMANTIC = "romantic"
    ROOF_WINDOW = "roof_window"
    ROOM_SERVICE = "room_service"
    SECURITY = "security"
    SHADES = "shades"
    SHOWER = "shower"
    SLEEP = "sleep"
    SMART_GLASS = "smart_glass"
    SPA = "spa"
    SPRINKLER = "sprinkler"
    TRAVEL = "travel"
    TURNTABLE = "turntable"
    UNLOCK = "unlock"
    VACATION = "vacation"
    WARNING = "warning"
    WATERFALL = "waterfall"
    WELCOME = "welcome"
    WINDOW = "window"
    WORK_OUT = "work_out"
    YOGA = "yoga"


@dataclass
class Icon(DataClassJSONMixin):
    """Icon."""

    icon: Icons


@dataclass
class Text(DataClassJSONMixin):
    """Icon."""

    text: str


class ButtonState(StrEnum):
    """State enum For Buttons."""

    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass
class Button(DataClassJSONMixin):
    """Button."""

    title: str
    # None is allowed during serializing, but not during deserializing
    content: Icon | Text | None
    subtitle: str = ""
    value: int = 0
    state: ButtonState = ButtonState.INACTIVE
    default: bool = False
    id: str = str(uuid1())

    def __post_init__(self) -> None:
        """Ensure value is in a valid range."""

        if self.value < MIN_VALUE or self.value > MAX_VALUE:
            msg = f"Button value must be in the range: {MIN_VALUE}..{MAX_VALUE}"
            raise ValueError(msg)


@dataclass
class Page(DataClassJSONMixin):
    """Page containing buttons."""

    title: str
    buttons: list[Button]
    id: str = str(uuid1())


@dataclass
class Configuration(DataClassJSONMixin):
    """Configuration of pages."""

    pages: list[Page]
    version: str = "1.0.1"
    id: str = str(uuid1())


@dataclass
class BaseConfiguration(DataClassJSONMixin):
    """Configuration of pages."""

    configuration: Configuration


class ButtonEventState(StrEnum):
    """State enum for ButtonEvent."""

    PRESSED = "pressed"
    RELEASED = "released"


@dataclass
class UpdateButton(DataClassJSONMixin):
    """UpdateButton."""

    id: str
    state: ButtonState = ButtonState.INACTIVE
    value: int = 0
    type: str = "button"


@dataclass
class ButtonEvent(DataClassJSONMixin):
    """ButtonEvent."""

    id: str
    state: ButtonEventState
    type: str = "button"


class PowerEventState(StrEnum):
    """State enum for PowerEvent."""

    CHARGING = "charging"
    FULL = "full"
    LOW = "low"
    CRITICAL = "critical"
    FAULT = "fault"
    DISCHARGING = "discharging"


@dataclass
class PowerEvent(DataClassJSONMixin):
    """PowerEvent."""

    type: str
    capacity: int
    state: PowerEventState


class StatusEventState(StrEnum):
    """State enum for StatusEvent."""

    OK = "ok"
    ERROR = "error"


@dataclass
class StatusEvent(DataClassJSONMixin):
    """StatusEvent."""

    type: str
    state: StatusEventState
    message: str | None = None


class SystemEventState(StrEnum):
    """State enum for SystemEvent."""

    ACTIVE = "active"
    STANDBY = "standby"
    SLEEP = "sleep"


@dataclass
class SystemEvent(DataClassJSONMixin):
    """SystemEvent."""

    type: str
    state: SystemEventState


@dataclass
class WheelEvent(DataClassJSONMixin):
    """WheelEvent."""

    type: str
    id: str
    counts: int


@dataclass
class BaseEvent(DataClassJSONMixin):
    """Base Event class."""

    event: WheelEvent | SystemEvent | StatusEvent | PowerEvent | ButtonEvent


@dataclass
class DisplayPage(DataClassJSONMixin):
    """DisplayPage."""

    pageid: str
    buttonid: str
    type: str = "displaypage"


@dataclass
class Notification(DataClassJSONMixin):
    """Notification."""

    id: str
    title: str
    subtitle: str
    type: str = "notification"


@dataclass
class BaseUpdate(DataClassJSONMixin):
    """Base Update Class."""

    update: UpdateButton | DisplayPage | Notification


class BaseWebSocketResponse(TypedDict):
    """Base class for serialized WebSocket events."""

    event: dict


WebSocketEventType = type[
    WheelEvent | SystemEvent | StatusEvent | PowerEvent | ButtonEvent
]


class Halo:
    """User friendly Mozart REST API and WebSocket client."""

    def __init__(self, host: str) -> None:
        """Initialize Mozart client."""
        self.host = host
        self.websocket_connected = False
        self.websocket_reconnect = False

        self._websocket_listener_active = False
        self._websocket_task: asyncio.Task
        self._websocket_queue: Queue = Queue()
        self._on_connection_lost: Callable[[None], Awaitable[None] | None] | None = None
        self._on_connection: Callable[[None], Awaitable[None] | None] | None = None

        self._on_all_events: Callable | None = None
        self._on_all_events_raw: Callable | None = None

        self._event_callbacks: dict[str, Callable | None] = defaultdict()
        self._event_callbacks.default_factory = lambda: None

    async def _check_websocket_connection(
        self,
    ) -> (
        Literal[True]
        | ClientConnectorError
        | ClientOSError
        | ServerTimeoutError
        | WSMessageTypeError
    ):
        """Check if a connection can be made to the device's WebSocket event channel."""
        try:
            async with (
                ClientSession(
                    timeout=ClientTimeout(connect=WEBSOCKET_TIMEOUT)
                ) as session,
                session.ws_connect(f"ws://{self.host}:8080/") as websocket,
            ):
                if await websocket.receive():
                    return True

        except (
            ClientConnectorError,
            ClientOSError,
            ServerTimeoutError,
            WSMessageTypeError,
        ) as error:
            return error

    async def check_device_connection(self, raise_error: bool = False) -> bool:
        """Check WebSocket connection."""
        # Don't use a taskgroup as both tasks should always be checked
        errors: tuple[
            Literal[True]
            | ClientConnectorError
            | ClientOSError
            | ServerTimeoutError
            | WSMessageTypeError
        ] = await asyncio.gather(  # type: ignore[assignment]
            self._check_websocket_connection(), return_exceptions=True
        )

        result = errors[0]

        # Check status
        if result is not True:
            if raise_error:
                raise result
            return False

        return result

    async def connect_events(self, reconnect: bool = False) -> None:
        """Start the WebSocket task."""
        self.websocket_reconnect = reconnect

        # Always add main WebSocket listener
        if not self._websocket_listener_active:
            self._websocket_task = asyncio.create_task(
                coro=self._websocket_connection(f"ws://{self.host}:8080/"),
                name=f"{self.host} - task",
            )

            self._websocket_listener_active = True

    async def disconnect_events(self) -> None:
        """Stop the WebSocket listener tasks."""
        self._websocket_listener_active = False
        self._websocket_task.cancel()

    async def _websocket_connection(self, host: str) -> None:
        """WebSocket listener."""
        while True:
            try:
                async with (
                    ClientSession(
                        timeout=ClientTimeout(connect=WEBSOCKET_TIMEOUT)
                    ) as session,
                    session.ws_connect(
                        url=host, heartbeat=WEBSOCKET_TIMEOUT
                    ) as websocket,
                ):
                    self.websocket_connected = True

                    if self._on_connection:
                        await self._trigger_callback(self._on_connection)

                    while self._websocket_listener_active:
                        with contextlib.suppress(asyncio.TimeoutError):
                            event = await websocket.receive_str(timeout=0.1)

                            await self._on_message(event)

                        with contextlib.suppress(QueueEmpty):
                            update = self._websocket_queue.get_nowait()
                            await websocket.send_str(cast(str, update))

                    self.websocket_connected = False
                    await websocket.close()
                    return

            except (
                ClientConnectorError,
                ClientOSError,
                TypeError,
                ServerTimeoutError,
                WSMessageTypeError,
            ) as error:
                if self.websocket_connected:
                    logger.debug("%s : %s - %s", host, type(error), error)
                    self.websocket_connected = False

                    if self._on_connection_lost:
                        await self._trigger_callback(self._on_connection_lost)

                if not self.websocket_reconnect:
                    logger.error("%s : %s - %s", host, type(error), error)
                    await self.disconnect_events()
                    return

                await asyncio.sleep(WEBSOCKET_TIMEOUT)

    async def send(self, data: BaseConfiguration | BaseUpdate) -> bool:
        """Send Configuration or Update. Return True if successful."""

        try:
            self._websocket_queue.put_nowait(data.to_json())
        except (QueueFull, QueueShutDown):
            return False
        else:
            return True

    async def _on_message(self, event: str) -> None:
        """Handle WebSocket events."""
        # Get the object type and deserialized object.
        try:
            deserialized_data = BaseEvent.from_json(event).event
        except (ValueError, AttributeError) as error:
            logger.error(
                "%s unable to deserialize WebSocket event: (%s) with error: (%s : %s)",
                self.host,
                event,
                type(error),
                error,
            )
            return

        # Handle all events if defined
        if self._on_all_events:
            await self._trigger_callback(
                self._on_all_events,
                deserialized_data,  # type: ignore[arg-type]
                underscore(deserialized_data.type),
            )

        if self._on_all_events_raw:
            await self._trigger_callback(self._on_all_events_raw, json.loads(event))

        # Handle specific events if defined
        triggered_event = self._event_callbacks[deserialized_data.type]

        if triggered_event:
            await self._trigger_callback(triggered_event, deserialized_data)  # type: ignore[arg-type]

    async def _trigger_callback(
        self,
        callback: Callable,
        *args: BaseWebSocketResponse | dict | str | WebSocketEventType,
    ) -> None:
        """Trigger async or sync callback correctly."""
        if asyncio.iscoroutinefunction(callback):
            await callback(*args)
        else:
            callback(*args)

    def get_on_connection_lost(self, on_connection_lost: Callable) -> None:
        """Set callback for WebSocket connection lost."""
        self._on_connection_lost = on_connection_lost

    def get_on_connection(self, on_connection: Callable) -> None:
        """Set callback for WebSocket connection."""
        self._on_connection = on_connection

    def get_all_events(
        self,
        on_all_events: Callable[[WebSocketEventType, str], Awaitable[None] | None],
    ) -> None:
        """Set callback for all events."""
        self._on_all_events = on_all_events

    def get_all_events_raw(
        self,
        on_all_events_raw: Callable[[BaseWebSocketResponse], Awaitable[None] | None],
    ) -> None:
        """Set callback for all events as dict."""
        self._on_all_events_raw = on_all_events_raw

    def get_wheel_event(
        self, on_wheel_event: Callable[[WheelEvent], Awaitable[None] | None]
    ) -> None:
        """Set callback for WheelEvent."""
        self._event_callbacks["wheel"] = on_wheel_event

    def get_system_event(
        self, on_system_event: Callable[[SystemEvent], Awaitable[None] | None]
    ) -> None:
        """Set callback for SystemEvent."""
        self._event_callbacks["system"] = on_system_event

    def get_status_event(
        self, on_status_event: Callable[[StatusEvent], Awaitable[None] | None]
    ) -> None:
        """Set callback for StatusEvent."""
        self._event_callbacks["status"] = on_status_event

    def get_power_event(
        self, on_power_event: Callable[[PowerEvent], Awaitable[None] | None]
    ) -> None:
        """Set callback for PowerEvent."""
        self._event_callbacks["power"] = on_power_event

    def get_button_event(
        self, on_button_event: Callable[[ButtonEvent], Awaitable[None] | None]
    ) -> None:
        """Set callback for ButtonEvent."""
        self._event_callbacks["button"] = on_button_event
