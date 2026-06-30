"""Models used for the Beoremote Halo client."""

from enum import Enum, StrEnum
import logging
from typing import Any, Literal, Self, TypedDict, cast
from uuid import UUID, uuid4

from pydantic import ConfigDict, Field, TypeAdapter, field_validator
from pydantic.dataclasses import dataclass
from pydantic_core import from_json, to_json

from .const import (
    BUTTON_CONTENT_TEXT_MAX_LENGTH,
    BUTTON_CONTENT_TEXT_MIN_LENGTH,
    BUTTON_SUBTITLE_MAX_LENGTH,
    BUTTON_SUBTITLE_MIN_LENGTH,
    BUTTON_TITLE_MAX_LENGTH,
    BUTTON_TITLE_MIN_LENGTH,
    MAX_BUTTONS,
    MAX_PAGES,
    MAX_VALUE,
    MIN_BUTTONS,
    MIN_PAGES,
    MIN_VALUE,
    NOTIFICATION_SUBTITLE_MAX_LENGTH,
    NOTIFICATION_SUBTITLE_MAX_LINE_LENGTH,
    NOTIFICATION_SUBTITLE_MAX_LINES,
    NOTIFICATION_SUBTITLE_MIN_LENGTH,
    NOTIFICATION_SUBTITLE_MIN_LINE_LENGTH,
    NOTIFICATION_SUBTITLE_MIN_LINES,
    NOTIFICATION_TITLE_MAX_LENGTH,
    NOTIFICATION_TITLE_MIN_LENGTH,
    PAGE_TITLE_MAX_LENGTH,
    PAGE_TITLE_MIN_LENGTH,
    VERSION,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(
    config=ConfigDict(
        validate_by_name=True, validate_by_alias=True, validate_assignment=True
    )
)
class _HaloConfigMixin:
    """Mixin for Beoremote Halo dataclass configuration."""

    def to_json(self) -> str:
        return to_json(self, exclude_none=True, by_alias=True).decode()

    @classmethod
    def from_json(cls, value: str) -> Self:
        return TypeAdapter(cls).validate_json(value, by_alias=True, by_name=True)

    def to_dict(self) -> dict[str, Any]:
        return cast(dict[str, Any], from_json(self.to_json()))

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Self:
        return TypeAdapter(cls).validate_python(value, by_alias=True, by_name=True)


@dataclass
class _HaloIdMixin:
    """Mixin for Beoremote Halo dataclasses that contain an ID.

    String values are accepted in the constructor, but are immediately converted to UUID.
    """

    # This is kw_only to ensure that it is placed at the end of constructor's of classes that inherit from this one
    id_: UUID | str = Field(
        serialization_alias="id",
        validation_alias="id",
        default_factory=uuid4,
        kw_only=True,
    )

    @property
    def uuid_id(self) -> UUID:
        """IDs are always converted to UUID, so only casting is necessary."""
        return cast("UUID", self.id_)

    @property
    def str_id(self) -> str:
        """String representation of ID."""
        return str(self.id_)

    @field_validator("id_", mode="after")
    @classmethod
    def valid_id_(cls, id_: UUID | str) -> UUID:
        """Check if provided string is a valid UUID.

        Returns:
            Valid ID in UUID form

        Raises:
            ValueError: Invalid UUID string
        """
        if isinstance(id_, str):
            try:
                return UUID(id_)
            except ValueError as e:
                msg = f"Malformed UUID str: {id_}"
                raise ValueError(msg) from e
        return id_


class UpdateTypes(StrEnum):
    """Values present in the `type` members of Update classes."""

    BUTTON = "button"
    DISPLAY_PAGE = "displaypage"
    NOTIFICATION = "notification"


class EventTypes(StrEnum):
    """Values present in the `type` members of Event classes."""

    BUTTON = "button"
    POWER = "power"
    STATUS = "status"
    SYSTEM = "system"
    WHEEL = "wheel"


class Icons(StrEnum):
    """Available icons for buttons.

    Each `Icon` has an 'active' and 'inactive' version, which is determined by a `Button`'s `ButtonState`.
    """

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
class Icon(_HaloConfigMixin):
    """Icon to be shown inside of a `Button`."""

    icon: Icons


@dataclass
class Text(_HaloConfigMixin):
    """Text to be shown inside of a `Button`.

    Args:
        text: Limited to 0-6
    """

    text: str = Field(
        min_length=BUTTON_CONTENT_TEXT_MIN_LENGTH,
        max_length=BUTTON_CONTENT_TEXT_MAX_LENGTH,
    )


class ButtonState(StrEnum):
    """Adjust the appearance of an `Icon` present on a `Button`. Has no effect on `Text`."""

    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass
class Button(_HaloConfigMixin, _HaloIdMixin):
    """An interact-able element that represents an action or physical device.

    Args:
        title: Limited to a length of 0-15
        content: Shown in the center of the `Button` on the Halo
        subtitle: Limited to a length of 0-15
        value: Limited to value of 0-100
        state: Overall state of the `Button`. Affects the `Icon` if configured
        default: `Button`s marked as default will be preselected when interacting with the Halo.
            Only a single Button can be default in a configuration
        id_: Unique identifier for the button. If no ID is provided, then one will be automatically generated

    """

    title: str = Field(
        min_length=BUTTON_TITLE_MIN_LENGTH, max_length=BUTTON_TITLE_MAX_LENGTH
    )
    content: Icon | Text = Field()
    subtitle: str | None = Field(
        default=None,
        min_length=BUTTON_SUBTITLE_MIN_LENGTH,
        max_length=BUTTON_SUBTITLE_MAX_LENGTH,
    )
    value: int | None = Field(default=None, ge=MIN_VALUE, le=MAX_VALUE)
    state: ButtonState | None = None
    default: bool | None = False


@dataclass
class Page(_HaloConfigMixin, _HaloIdMixin):
    """Group of `Button` elements grouped with a title in the `Configuration`.

    Args:
        title: Limited to a length of  0-40
        buttons: Group of `Button` elements. Limited to a length of 0-8
        id_: Unique identifier for the button. If no ID is provided, then one will be automatically generated
    """

    title: str = Field(
        min_length=PAGE_TITLE_MIN_LENGTH, max_length=PAGE_TITLE_MAX_LENGTH
    )
    buttons: list[Button] = Field(min_length=MIN_BUTTONS, max_length=MAX_BUTTONS)

    @field_validator("buttons", mode="after")
    @classmethod
    def valid_default(cls, buttons: list[Button]) -> list[Button]:
        """Check if provided buttons only contain at most 1 default button.

        Returns:
            Defined buttons

        Raises:
            ValueError: More than 1 default button
        """
        default_buttons = [button for button in buttons if button.default is True]

        if len(default_buttons) > 1:
            msg = f"Only a single Button can be default per configuration. Default buttons found {default_buttons}"
            raise ValueError(msg)
        return buttons


@dataclass
class Configuration(_HaloConfigMixin, _HaloIdMixin):
    """Main Configuration class.

    Args:
        pages: Group of `Page` elements. Limited to a length of 1-3
        version: Version of the API
        id_: Unique identifier for the button. If no ID is provided, then one will be automatically generated
    """

    pages: list[Page] = Field(min_length=MIN_PAGES, max_length=MAX_PAGES)
    version: str = Field(VERSION, init=False)

    @field_validator("pages", mode="after")
    @classmethod
    def valid_default(cls, pages: list[Page]) -> list[Page]:
        """Check if provided pages only contain at most 1 default button.

        Returns:
            Defined pages

        Raises:
            ValueError: More than 1 default button
        """
        default_buttons: list[Button] = []
        for page in pages:
            default_buttons.extend(
                button for button in page.buttons if button.default is True
            )

        if len(default_buttons) > 1:
            msg = f"Only a single Button can be default per configuration. Default buttons found {default_buttons}"
            raise ValueError(msg)
        return pages


@dataclass
class BaseConfiguration(_HaloConfigMixin):
    """Root configuration class.

    Args:
        configuration: Main configuration class
    """

    configuration: Configuration


class ButtonEventState(StrEnum):
    """Available states for `ButtonEvent`."""

    PRESSED = "pressed"
    RELEASED = "released"


@dataclass
class ButtonEvent(_HaloConfigMixin, _HaloIdMixin):
    """Button event received from the Halo."""

    state: ButtonEventState
    type_: Literal[EventTypes.BUTTON] = Field(serialization_alias="type", init=False)


class PowerEventState(StrEnum):
    """Available states for `PowerEvent`."""

    CHARGING = "charging"
    FULL = "full"
    LOW = "low"
    CRITICAL = "critical"
    FAULT = "fault"
    DISCHARGING = "discharging"


@dataclass
class PowerEvent(_HaloConfigMixin):
    """Power event received from the Halo.

    Contains the battery capacity and the (new) power state.
    """

    capacity: int
    state: PowerEventState
    type_: Literal[EventTypes.POWER] = Field(
        default=EventTypes.POWER, serialization_alias="type"
    )


class StatusEventState(StrEnum):
    """Available states for `StatusEvent`."""

    OK = "ok"
    ERROR = "error"


@dataclass
class StatusEvent(_HaloConfigMixin):
    """Status event received from the Halo.

    Contains a message and state.

    Various status messages can be received, but some common are:

    Valid configuration:
        `message: 'configuration', state: 'ok'`

    Valid update:
        `message: 'update', state: 'ok'`

    New client replacing WebSocket connection:
        `message: 'Client connection replaced, previous: <ip_address>, now: <ip_address>', state: 'ok'`

    Invalid button id referenced while sending `UpdateButton`:
        `message: 'The button id was not found the the configuration: <id>, state: 'error'`

    Invalid page and button ids referenced while sending `UpdateDisplayPage`:
        `message: 'homeautomationsystem::message::Update|homeautomationsystem::schema::Update::UpdateProperty [No oneof found] {'page_id':'<page_id>', 'button_id':'<page_id>', 'type':'displaypage'}', state: 'error'`
    """

    state: StatusEventState
    message: str | None = None
    type_: Literal[EventTypes.STATUS] = Field(
        default=EventTypes.STATUS,
        serialization_alias="type",
        validation_alias="type",
    )


class SystemEventState(StrEnum):
    """Available states for `SystemEvent`."""

    ACTIVE = "active"
    STANDBY = "standby"
    SLEEP = "sleep"


@dataclass
class SystemEvent(_HaloConfigMixin):
    """System event received from the Halo.

    Contains state describing state of the system.
    """

    state: SystemEventState
    type_: Literal[EventTypes.SYSTEM] = Field(
        default=EventTypes.SYSTEM,
        serialization_alias="type",
        validation_alias="type",
    )


class WheelEventValues(Enum):
    """Available values for `counts` received in `WheelEvent`."""

    WHEEL_CLOCKWISE_NORMAL = 1
    WHEEL_CLOCKWISE_FAST = 2
    WHEEL_CLOCKWISE_MODERATELY_FAST = 3
    WHEEL_CLOCKWISE_VERY_FAST = 4
    WHEEL_CLOCKWISE_EXTREMELY_FAST = 5
    WHEEL_COUNTER_CLOCKWISE_NORMAL = -1
    WHEEL_COUNTER_CLOCKWISE_FAST = -2
    WHEEL_COUNTER_CLOCKWISE_MODERATELY_FAST = -3
    WHEEL_COUNTER_CLOCKWISE_VERY_FAST = -4
    WHEEL_COUNTER_CLOCKWISE_EXTREMELY_FAST = -5


@dataclass
class WheelEvent(_HaloConfigMixin, _HaloIdMixin):
    """Wheel event received from the Halo.

    Contains id of button and momentum-affected counts value with value range -5..5.

    A `WheelEvent` is only sent when the 'wheel' is used on a `Button`.
    The direction of the wheel can be determined by the value of 'counts': positive value -> clockwise, negative value -> counter-clockwise.
    The momentum of the wheel can also be determined by the counts value: 1 -> slow clockwise movement, 5 -> very fast clockwise movement.
    """

    counts: WheelEventValues
    type_: Literal[EventTypes.WHEEL] = Field(
        default=EventTypes.WHEEL,
        serialization_alias="type",
        validation_alias="type",
    )


@dataclass
class Event(_HaloConfigMixin):
    """Base Event class."""

    event: WheelEvent | SystemEvent | StatusEvent | PowerEvent | ButtonEvent


@dataclass
class UpdateButton(_HaloConfigMixin, _HaloIdMixin):
    """Button update to be sent to the Halo.

    Sending this will update the defined attributes of a single `Button` in a configuration.

    Args:
        state: State to update
        value: Value to update
        title: Title to update
        subtitle: Subtitle to update
        content: Content to update
    """

    state: ButtonState | None = None
    value: int | None = Field(default=None, ge=MIN_VALUE, le=MAX_VALUE)
    title: str | None = Field(
        default=None,
        min_length=BUTTON_TITLE_MIN_LENGTH,
        max_length=BUTTON_TITLE_MAX_LENGTH,
    )
    subtitle: str | None = Field(
        default=None,
        min_length=BUTTON_SUBTITLE_MIN_LENGTH,
        max_length=BUTTON_SUBTITLE_MAX_LENGTH,
    )
    content: Text | Icon | None = None
    type_: Literal[UpdateTypes.BUTTON] = Field(
        default=UpdateTypes.BUTTON, serialization_alias="type", init=False
    )


@dataclass
class UpdateDisplayPage(_HaloConfigMixin):
    """Display a specific `Page` and `Button`.

    Sending this will make the Halo focus on a specified button on a page.

    Args:
        page_id: UUID of page to display
        button_id: UUID of button in page to display
    """

    page_id: UUID = Field(serialization_alias="pageid")
    button_id: UUID | None = Field(default=None, serialization_alias="buttonid")
    type_: Literal[UpdateTypes.DISPLAY_PAGE] = Field(
        default=UpdateTypes.DISPLAY_PAGE, serialization_alias="type", init=False
    )


@dataclass
class UpdateNotification(_HaloConfigMixin, _HaloIdMixin):
    """Display a notification message.

    Sending this will make the Halo show a notification box with the defined title and message.

    Args:
        title: Title of notification
        message: Message to display in notification
    """

    title: str | None = Field(
        default=None,
        min_length=NOTIFICATION_TITLE_MIN_LENGTH,
        max_length=NOTIFICATION_TITLE_MAX_LENGTH,
    )
    message: str | None = Field(default=None, serialization_alias="subtitle")
    type_: Literal[UpdateTypes.NOTIFICATION] = Field(
        default=UpdateTypes.NOTIFICATION, serialization_alias="type", init=False
    )

    @field_validator("message", mode="after")
    @classmethod
    def valid_message(cls, message: str | None) -> str | None:
        """Check if notification has valid formatting.

        Returns:
            Defined message

        Raises:
            ValueError: Invalid notification formatting
        """
        if message is not None:
            # Overall length
            if (
                message_length := len(message)
            ) and message_length > NOTIFICATION_SUBTITLE_MAX_LENGTH:
                msg = f"Defined message contains too many characters. Valid range: {NOTIFICATION_SUBTITLE_MIN_LENGTH}..{NOTIFICATION_SUBTITLE_MAX_LENGTH}"
                raise ValueError(msg)
            # Number of lines
            if (message_lines := message.splitlines()) and len(
                message_lines
            ) > NOTIFICATION_SUBTITLE_MAX_LINES:
                msg = f"Defined message contains too many lines: {len(message_lines)}. Valid range: {NOTIFICATION_SUBTITLE_MIN_LINES}..{NOTIFICATION_SUBTITLE_MAX_LINES}"
                raise ValueError(msg)
            # Length of each line
            for line in message_lines:
                if (
                    line_length := len(line)
                ) and line_length > NOTIFICATION_SUBTITLE_MAX_LINE_LENGTH:
                    msg = f"Defined message contains a line with too many characters: {line_length}. Valid range: {NOTIFICATION_SUBTITLE_MIN_LINE_LENGTH}..{NOTIFICATION_SUBTITLE_MAX_LINE_LENGTH}"
                    raise ValueError(msg)

        return message


@dataclass
class Update(_HaloConfigMixin):
    """An update to be sent to the Beoremote Halo."""

    update: UpdateButton | UpdateDisplayPage | UpdateNotification


class BaseWebSocketResponse(TypedDict):
    """Base class for serialized WebSocket events."""

    event: dict


EventType = WheelEvent | SystemEvent | StatusEvent | PowerEvent | ButtonEvent
