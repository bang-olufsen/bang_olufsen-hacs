"""Various utilities for Bang & Olufsen testing."""

from inflection import underscore

from homeassistant.components.bang_olufsen.const import (
    BEO_REMOTE_CONTROL_KEYS,
    BEO_REMOTE_KEYS,
    BEO_REMOTE_SUBMENU_CONTROL,
    BEO_REMOTE_SUBMENU_LIGHT,
    DEVICE_BUTTONS,
    BeoButtons,
)

from .const import (
    TEST_MEDIA_PLAYER_ENTITY_ID,
    TEST_MEDIA_PLAYER_ENTITY_ID_4,
    TEST_PROXIMITY_EVENT_ENTITY_ID,
    TEST_REMOTE_SERIAL,
    TEST_SERIAL_NUMBER,
)


def get_balance_entity_ids() -> list[str]:
    """Return a list of entity_ids that the Beosound Balance provides."""
    entity_ids: list[str] = [
        TEST_MEDIA_PLAYER_ENTITY_ID,
        TEST_PROXIMITY_EVENT_ENTITY_ID,
    ]
    entity_ids.extend(
        [
            f"event.beosound_balance_11111111_{underscore(button_type)}".replace(
                "preset", "favorite_"
            )
            for button_type in DEVICE_BUTTONS
        ]
    )

    return entity_ids


def get_premiere_entity_ids() -> list[str]:
    """Return a list of entity_ids that the Beosound Premiere provides."""
    entity_ids: list[str] = [TEST_MEDIA_PLAYER_ENTITY_ID_4]

    premiere_buttons = DEVICE_BUTTONS.copy()
    premiere_buttons.remove(BeoButtons.BLUETOOTH.value)

    entity_ids.extend(
        [
            f"event.beosound_premiere_44444444_{underscore(button_type)}".replace(
                "preset", "favorite_"
            )
            for button_type in premiere_buttons
        ]
    )

    return entity_ids


def get_remote_entity_ids(
    remote_serial: str = TEST_REMOTE_SERIAL, device_serial: str = TEST_SERIAL_NUMBER
) -> list[str]:
    """Return a list of entity_ids that the Beoremote One provides."""
    entity_ids: list[str] = [
        f"sensor.beoremote_one_{remote_serial}_{device_serial}_battery_level"
    ]

    # Add remote light key Event entity ids
    entity_ids.extend(
        [
            f"event.beoremote_one_{remote_serial}_{device_serial}_{BEO_REMOTE_SUBMENU_LIGHT.lower()}_{key_type.lower()}".replace(
                "func", "function_"
            ).replace("digit", "digit_")
            for key_type in BEO_REMOTE_KEYS
        ]
    )

    # Add remote control key Event entity ids
    entity_ids.extend(
        [
            f"event.beoremote_one_{remote_serial}_{device_serial}_{BEO_REMOTE_SUBMENU_CONTROL.lower()}_{key_type.lower()}".replace(
                "func", "function_"
            ).replace("digit", "digit_")
            for key_type in (*BEO_REMOTE_KEYS, *BEO_REMOTE_CONTROL_KEYS)
        ]
    )

    return entity_ids
