"""Various utilities for Beoremote Halo."""

import numpy as np

from .const import MAX_VALUE, MIN_VALUE


def clamp_button_value(value: float) -> int:
    """Clamp a value to work with Halo `Button`s minimum and maximum values.

    Args:
        value: Value to be clamped.

    Returns:
        Clamped value.

    """
    return int(np.clip(value, MIN_VALUE, MAX_VALUE))


def interpolate_button_value(value: float, min_value: float, max_value: float) -> int:
    """Interpolate a value to work with Halo `Button`s minimum and maximum values.

    Args:
        value: Value to be interpolated.
        min_value: Minimum value to interpolate from.
        max_value: Maximum value to interpolate to.

    Returns:
        Interpolated value.

    """
    return int(np.interp(value, [min_value, max_value], [MIN_VALUE, MAX_VALUE]))
