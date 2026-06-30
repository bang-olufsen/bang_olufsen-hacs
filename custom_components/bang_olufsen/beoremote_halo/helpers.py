"""Various helpers for configuration manipulation."""

from uuid import UUID

from . import MAX_VALUE, MIN_VALUE
from .models import BaseConfiguration, Button, ButtonState, Icon, Page, Text


# Configuration modification helper methods
def clear_default_button(configuration: BaseConfiguration) -> None:
    """Remove the default flag from a configuration if present."""
    if (button := get_default_button(configuration)) is not None:
        page_idx, button_idx = get_button_indices(configuration, button.uuid_id)
        configuration.configuration.pages[page_idx].buttons[button_idx].default = False


def update_button(
    configuration: BaseConfiguration,
    id_: UUID,
    title: str | None = None,
    content: Icon | Text | None = None,
    subtitle: str | None = None,
    value: int | None = None,
    state: ButtonState | None = None,
    default: bool | None = None,
) -> None:
    """Update a `Button`s attributes.

    Attributes that are set to `None` are left unmodified.

    Raises:
        ValueError: value is outside the valid range og 0-100 or multiple default buttons have been defined
    """
    # Get button's indices to modify values in configuration
    page_idx, button_idx = get_button_indices(configuration, id_)

    if title is not None:
        configuration.configuration.pages[page_idx].buttons[button_idx].title = title
    if content is not None:
        configuration.configuration.pages[page_idx].buttons[
            button_idx
        ].content = content
    if subtitle is not None:
        configuration.configuration.pages[page_idx].buttons[
            button_idx
        ].subtitle = subtitle
    if value is not None:
        if value < MIN_VALUE or value > MAX_VALUE:
            msg = f"Invalid button value: {value}. Button value must be in the range: {MIN_VALUE}-{MAX_VALUE}"
            raise ValueError(msg)
        configuration.configuration.pages[page_idx].buttons[button_idx].value = value
    if state is not None:
        configuration.configuration.pages[page_idx].buttons[button_idx].state = state
    if default is not None:
        if (
            default is True
            and (button := get_default_button(configuration))
            and button.uuid_id != id_
        ):
            msg = f"Default button already defined: {button}. Clear existing default button before setting new one"
            raise ValueError(msg)
        configuration.configuration.pages[page_idx].buttons[
            button_idx
        ].default = default


def update_page(
    configuration: BaseConfiguration,
    id_: UUID,
    title: str | None = None,
    buttons: list[Button] | None = None,
) -> None:
    """Update a `Page`s attributes.

    Attributes that are set to `None` are left unmodified.
    """
    # Get page index
    page_idx = get_page_index(configuration, id_)

    if title is not None:
        configuration.configuration.pages[page_idx].title = title
    if buttons is not None:
        configuration.configuration.pages[page_idx].buttons = buttons


def delete_button(configuration: BaseConfiguration, id_: UUID) -> None:
    """Delete a `Button` from a configuration."""
    page_idx, button_idx = get_button_indices(configuration, id_)
    configuration.configuration.pages[page_idx].buttons.pop(button_idx)


def delete_page(configuration: BaseConfiguration, id_: UUID) -> None:
    """Delete a `Page` from a configuration."""
    configuration.configuration.pages.pop(get_page_index(configuration, id_))


# Configuration get helper methods
def get_button_indices(configuration: BaseConfiguration, id_: UUID) -> tuple[int, int]:
    """Get `Page` and `Button` indices in configuration from `Button` ID.

    Returns:
        `Page` index, `Button` index

    Raises:
        ValueError: `Button` ID can't be found in configuration
    """
    for page_idx, page in enumerate(configuration.configuration.pages):
        for button_idx, button in enumerate(page.buttons):
            if button.uuid_id == id_:
                return (page_idx, button_idx)
    msg = f"Unable to get indices for Button with ID: {id_}"
    raise ValueError(msg)


def get_page_index(configuration: BaseConfiguration, id_: UUID) -> int:
    """Get `Page` index in configuration from `Page` ID.

    Returns:
        `Page` index

    Raises:
        ValueError: `Page` ID can't be found in configuration
    """
    for page_idx, page in enumerate(configuration.configuration.pages):
        if page.uuid_id == id_:
            return page_idx
    msg = f"Unable to get index for Page with ID: {id_}"
    raise ValueError(msg)


def get_page_from_id(configuration: BaseConfiguration, id_: UUID) -> Page:
    """Get `Page` in configuration from `Page` ID.

    Returns:
        `Page`

    Raises:
        ValueError: `Page` ID can't be found in configuration
    """
    for page in configuration.configuration.pages:
        if page.uuid_id == id_:
            return page
    msg = f"Unable to get Page with ID: {id_}"
    raise ValueError(msg)


def get_button_from_id(configuration: BaseConfiguration, id_: UUID) -> Button:
    """Get `Button` in configuration from `Button` ID.

    Returns:
        `Button`

    Raises:
        ValueError: If the button can't be found
    """
    for page in configuration.configuration.pages:
        for button in page.buttons:
            if button.uuid_id == id_:
                return button
    msg = f"Unable to get Button with ID: {id_}"
    raise ValueError(msg)


def get_default_button(configuration: BaseConfiguration) -> Button | None:
    """Get the default `Button` from configuration if available.

    Returns:
        `Button` or None
    """
    for page in configuration.configuration.pages:
        for button in page.buttons:
            if button.default is True:
                return button
    return None


def get_all_buttons(configuration: BaseConfiguration) -> list[Button]:
    """Get all `Button`s from all pages in configuration.

    Returns:
        List of `Button`s
    """
    return [
        button for page in configuration.configuration.pages for button in page.buttons
    ]
