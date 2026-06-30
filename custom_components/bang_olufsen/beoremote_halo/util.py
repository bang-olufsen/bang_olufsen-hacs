"""Various utilities for Beoremote Halo."""

from .const import (
    BUTTON_CONTENT_TEXT_MAX_LENGTH,
    BUTTON_SUBTITLE_MAX_LENGTH,
    BUTTON_TITLE_MAX_LENGTH,
    MAX_VALUE,
    MIN_VALUE,
    PAGE_TITLE_MAX_LENGTH,
)


def clamp_button_value(value: float) -> int:
    """Clamp a value to work with Halo `Button`s minimum and maximum values.

    Args:
        value: Value to be clamped

    Returns:
        Clamped value
    """
    return max(MIN_VALUE, min(int(value), MAX_VALUE))


def interpolate_button_value(value: float, min_value: float, max_value: float) -> int:
    """Interpolate a value to work with Halo `Button`s minimum and maximum values.

    Args:
        value: Value to be interpolated
        min_value: Minimum value to interpolate from
        max_value: Maximum value to interpolate to

    Returns:
        Interpolated value
    """
    return int(
        ((value - min_value) / (max_value - min_value)) * (MAX_VALUE - MIN_VALUE)
        + MIN_VALUE
    )


def trim_button_text(text: str) -> str:
    """Shorten a string to fit into a button's text.

    Args:
        text: String to be shortened

    Returns:
        Shortened string
    """
    return text[0:BUTTON_CONTENT_TEXT_MAX_LENGTH]


def trim_button_subtitle(text: str) -> str:
    """Shorten a string to fit into a button's subtitle.

    Args:
        text: String to be shortened

    Returns:
        Shortened string
    """
    return text[0:BUTTON_SUBTITLE_MAX_LENGTH]


def trim_button_title(text: str) -> str:
    """Shorten a string to fit into a button's title.

    Args:
        text: String to be shortened

    Returns:
        Shortened string
    """
    return text[0:BUTTON_TITLE_MAX_LENGTH]


def trim_page_title(text: str) -> str:
    """Shorten a string to fit into a page's title.

    Args:
        text: String to be shortened

    Returns:
        Shortened string
    """
    return text[0:PAGE_TITLE_MAX_LENGTH]
