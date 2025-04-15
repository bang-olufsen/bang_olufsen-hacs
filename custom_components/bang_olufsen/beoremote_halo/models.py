"""Models used for the Beoremote Halo client."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypedDict
from uuid import uuid1

from mashumaro import field_options
from mashumaro.mixins.json import DataClassJSONMixin

from .const import MAX_VALUE, MIN_VALUE, VERSION


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
class Icon(DataClassJSONMixin):
    """Icon to be shown inside of a `Button`."""

    icon: Icons


@dataclass
class Text(DataClassJSONMixin):
    """Text to be shown inside of a `Button`."""

    text: str


class ButtonState(StrEnum):
    """Adjust the appearance of an `Icon` present on a `Button`. Has no effect on `Text`."""

    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass
class Button(DataClassJSONMixin):
    """An interactable element that represents an action or physical device.

    Contains a title, content (either an icon or text), subtitle, value, state and if it is the default.
    `Button`s marked as default will be pre-selected when interacting with the Halo. Only a single Button can be default in a configuration.

    Ensures that the value is in the supported range.
    """

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
            raise ValueError(
                f"Button value must be in the range: {MIN_VALUE}..{MAX_VALUE}"
            )


@dataclass
class Page(DataClassJSONMixin):
    """Group of `Button` elements grouped with a title in the `Configuration`.

    Contains a title, a list of buttons and an id.

    Ensures that at most 8 buttons are in a page.
    """

    title: str
    buttons: list[Button]
    id: str = str(uuid1())

    def __post_init__(self) -> None:
        """Ensure configuration is valid."""

        # Ensure that there are no more than 3 pages.
        if len(self.buttons) > 8:
            raise ValueError("Only 8 buttons are allowed in a page.")


@dataclass
class Configuration(DataClassJSONMixin):
    """Main Configuration class.

    Contains a list of pages, the version of the API client and an ID.

    Ensures that at most one `Button` is marked default.
    Ensures that at most 3 pages are in a configuration.
    """

    pages: list[Page]
    version: str = VERSION
    id: str = str(uuid1())

    def __post_init__(self) -> None:
        """Ensure configuration is valid."""

        # Ensure that at most one Button is marked as default.
        default_buttons: list[Button] = []
        for page in self.pages:
            default_buttons.extend(
                button for button in page.buttons if button.default is True
            )

        if len(default_buttons) > 1:
            raise ValueError(
                f"Only a single Button can be default per configuration. Default buttons found {default_buttons}"
            )

        # Ensure that there are no more than 3 pages.
        if len(self.pages) > 3:
            raise ValueError("Only 3 pages are allowed per configuration.")


@dataclass
class BaseConfiguration(DataClassJSONMixin):
    """Root configuration class.

    Contains the main configuration class.
    """

    configuration: Configuration


class ButtonEventState(StrEnum):
    """Available states for `ButtonEvent`."""

    PRESSED = "pressed"
    RELEASED = "released"


@dataclass
class ButtonEvent(DataClassJSONMixin):
    """Button event received from the Halo.

    Contains the id and the (new) state of the button.
    """

    id: str
    state: ButtonEventState
    type: str = field(default="button", init=False)


class PowerEventState(StrEnum):
    """Available states for `PowerEvent`."""

    CHARGING = "charging"
    FULL = "full"
    LOW = "low"
    CRITICAL = "critical"
    FAULT = "fault"
    DISCHARGING = "discharging"


@dataclass
class PowerEvent(DataClassJSONMixin):
    """Power event received from the Halo.

    Contains the battery capacity and the (new) power state.
    """

    capacity: int
    state: PowerEventState
    type: str = field(default="power", init=False)


class StatusEventState(StrEnum):
    """Available states for `StatusEvent`."""

    OK = "ok"
    ERROR = "error"


@dataclass
class StatusEvent(DataClassJSONMixin):
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
    type: str = field(default="status", init=False)


class SystemEventState(StrEnum):
    """Available states for `SystemEvent`."""

    ACTIVE = "active"
    STANDBY = "standby"
    SLEEP = "sleep"


@dataclass
class SystemEvent(DataClassJSONMixin):
    """System event received from the Halo.

    Contains state describing state of the system.
    """

    state: SystemEventState
    type: str = field(default="system", init=False)


@dataclass
class WheelEvent(DataClassJSONMixin):
    """Wheel event received from the Halo.

    Contains id of button and momentum-affected counts value with value range -5..5.

    A `WheelEvent` is only sent when the 'wheel' is used on a `Button`.
    The direction of the wheel can be determined by the value of 'counts': positive value -> clockwise, negative value -> counter-clockwise.
    The momentum of the wheel can also be determined by the counts value: 1 -> slow clockwise movement, 5 -> very fast clockwise movement.
    """

    id: str
    counts: int
    type: str = field(default="wheel", init=False)


@dataclass
class Event(DataClassJSONMixin):
    """Base Event class."""

    event: WheelEvent | SystemEvent | StatusEvent | PowerEvent | ButtonEvent


@dataclass
class UpdateButton(DataClassJSONMixin):
    """Button update to be sent to the Halo.

    Contains id, state and value.

    Sending this will update the state and value of a single `Button` in a configuration.
    """

    id: str
    state: ButtonState = ButtonState.INACTIVE
    value: int = 0
    type: str = field(default="button", init=False)

    def __post_init__(self) -> None:
        """Ensure value is in a valid range."""
        if self.value < MIN_VALUE or self.value > MAX_VALUE:
            raise ValueError(
                f"Button value must be in the range: {MIN_VALUE}..{MAX_VALUE}"
            )


@dataclass
class UpdateDisplayPage(DataClassJSONMixin):
    """Display a specific `Page` and `Button`.

    Contains page and button id.

    Sending this will make the Halo focus on a specified button on a page.
    """

    page_id: str = field(metadata=field_options(alias="pageid"))
    button_id: str = field(metadata=field_options(alias="buttonid"))
    type: str = field(default="displaypage", init=False)


@dataclass
class UpdateNotification(DataClassJSONMixin):
    """Notification."""

    title: str
    subtitle: str
    type: str = field(default="notification", init=False)
    id: str = str(uuid1())


@dataclass
class Update(DataClassJSONMixin):
    """Update."""

    update: UpdateButton | UpdateDisplayPage | UpdateNotification


class BaseWebSocketResponse(TypedDict):
    """Base class for serialized WebSocket events."""

    event: dict


EventType = WheelEvent | SystemEvent | StatusEvent | PowerEvent | ButtonEvent
