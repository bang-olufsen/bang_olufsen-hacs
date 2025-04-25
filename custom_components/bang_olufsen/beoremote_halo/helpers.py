"""Various helpers for configuration manipulation."""

from .models import BaseConfiguration, Button, ButtonState, Icon, Page, Text


# Configuration modification helper methods
def clear_default_button(configuration: BaseConfiguration) -> BaseConfiguration:
    """Remove the default flag from a configuration if present.

    Returns:
        Modified configuration or unmodified if default was not set.

    """
    if (button := get_default_button(configuration)) is not None:
        configuration = set_default_button(configuration, button.id, False)
    return configuration


def set_default_button(
    configuration: BaseConfiguration, button_id: str, default: bool
) -> BaseConfiguration:
    """Set the default flag for a `Button` in a configuration.

    Returns:
        Modified configuration.

    """
    page_idx, button_idx = get_button_indices(configuration, button_id)
    configuration.configuration.pages[page_idx].buttons[button_idx].default = default
    return configuration


def update_button(
    configuration: BaseConfiguration,
    id: str,
    title: str | None = None,
    content: Icon | Text | None = None,
    subtitle: str | None = None,
    value: int | None = None,
    state: ButtonState | None = None,
    default: bool | None = None,
) -> BaseConfiguration:
    """Update a `Button`s attributes.

    Attributes that are set to `None` are left unmodified

    Returns:
        Modified configuration.

    """
    # Get button's indices to modify values in configuration
    page_idx, button_idx = get_button_indices(configuration, id)

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
        configuration.configuration.pages[page_idx].buttons[button_idx].value = value
    if state is not None:
        configuration.configuration.pages[page_idx].buttons[button_idx].state = state
    if default is not None:
        configuration.configuration.pages[page_idx].buttons[
            button_idx
        ].default = default

    return configuration


def update_page(
    configuration: BaseConfiguration,
    id: str,
    title: str | None = None,
    buttons: list[Button] | None = None,
) -> BaseConfiguration:
    """Update a `Page`s attributes.

    Attributes that are set to `None` are left unmodified

    Returns:
        Modified configuration.

    """
    # Get page index
    page_idx = get_page_index(configuration, id)

    if title is not None:
        configuration.configuration.pages[page_idx].title = title
    if buttons is not None:
        configuration.configuration.pages[page_idx].buttons = buttons

    return configuration


def delete_button(configuration: BaseConfiguration, id: str) -> BaseConfiguration:
    """Delete a `Button` from a configuration.

    Returns:
        Modified configuration.

    """
    page_idx, button_idx = get_button_indices(configuration, id)
    configuration.configuration.pages[page_idx].buttons.pop(button_idx)
    return configuration


def delete_page(configuration: BaseConfiguration, id: str) -> BaseConfiguration:
    """Delete a `Page` from a configuration.

    Returns:
        Modified configuration.

    """
    configuration.configuration.pages.pop(get_page_index(configuration, id))
    return configuration


# Configuration get helper methods
def get_button_indices(configuration: BaseConfiguration, id: str) -> tuple[int, int]:
    """Get `Page` and `Button` indices in configuration from `Button` ID.

    Raises:
        ValueError: `Button` ID can't be found in configuration.

    Returns:
        `Page` index, `Button` index.

    """

    for page_idx, page in enumerate(configuration.configuration.pages):
        for button_idx, button in enumerate(page.buttons):
            if button.id == id:
                return (page_idx, button_idx)
    raise ValueError(f"Unable to get indices for: {id}")


def get_page_index(configuration: BaseConfiguration, id: str) -> int:
    """Get `Page` index in configuration from `Page` ID.

    Raises:
        ValueError: `Page` ID can't be found in configuration.

    Returns:
        `Page` index.

    """
    for page_idx, page in enumerate(configuration.configuration.pages):
        if page.id == id:
            return page_idx
    raise ValueError(f"Unable to get index for: {id}")


def get_page_from_id(configuration: BaseConfiguration, page_id: str) -> Page:
    """Get `Page` in configuration from `Page` ID.

    Raises:
        ValueError: `Page` ID can't be found in configuration.

    Returns:
        `Page`.

    """
    for page in configuration.configuration.pages:
        if page.id == page_id:
            return page
    raise ValueError(f"Unable to get Page with ID: {id}")


def get_button_from_id(
    configuration: BaseConfiguration, button_id: str
) -> Button | None:
    """Get `Button` in configuration from `Button` ID.

    Returns:
        `Button` or None if `Button` can't be found.

    """
    for page in configuration.configuration.pages:
        for button in page.buttons:
            if button.id == button_id:
                return button
    return None


def get_default_button(configuration: BaseConfiguration) -> Button | None:
    """Get the default `Button` from configuration if available.

    Returns:
        `Button` or None.

    """
    for page in configuration.configuration.pages:
        for button in page.buttons:
            if button.default is True:
                return button
    return None


def get_all_buttons(configuration: BaseConfiguration) -> list[Button]:
    """Get all `Button`s from all pages in configuration.

    Returns:
        List of `Button`s.

    """
    return [
        button for page in configuration.configuration.pages for button in page.buttons
    ]
