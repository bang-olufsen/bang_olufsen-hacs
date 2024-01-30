"""Various utilities for the Bang & Olufsen integration."""

from __future__ import annotations

from . import BangOlufsenData


def set_platform_initialized(data: BangOlufsenData) -> None:
    """Increment platforms_initialized to indicate that a platform has been initialized."""
    data.platforms_initialized += 1
