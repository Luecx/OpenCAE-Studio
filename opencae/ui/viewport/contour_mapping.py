"""Normalize contour presentation settings for result renderers."""

from __future__ import annotations

DEFAULT_CONTOUR_LEVELS = 18
MIN_CONTOUR_LEVELS = 2
MAX_CONTOUR_LEVELS = 32
CONTINUOUS_COLOR_COUNT = 256
DEFAULT_OUTSIDE_COLOR = "#8a8f94"


def contour_plot_kwargs(settings=None):
    """Return PyVista color-mapping kwargs for one contour configuration."""
    settings = settings or {}
    continuous = bool(settings.get("continuous", False))
    levels = _clamped_levels(settings.get("levels", DEFAULT_CONTOUR_LEVELS))
    outside = bool(settings.get("outside_colors", True))
    below = str(settings.get("below_color", DEFAULT_OUTSIDE_COLOR)) if outside else None
    above = str(settings.get("above_color", DEFAULT_OUTSIDE_COLOR)) if outside else None
    return {
        "n_colors": CONTINUOUS_COLOR_COUNT if continuous else levels,
        "below_color": below,
        "above_color": above,
    }


def _clamped_levels(value):
    """Return a valid discrete contour-level count from stored/UI input."""
    try:
        levels = int(value)
    except (TypeError, ValueError):
        levels = DEFAULT_CONTOUR_LEVELS
    return max(MIN_CONTOUR_LEVELS, min(MAX_CONTOUR_LEVELS, levels))
