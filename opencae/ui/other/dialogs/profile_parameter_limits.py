"""Defines bounded UI ranges for the existing profile parameter keys."""

from __future__ import annotations

import math
from collections.abc import Mapping

from PyQt6.QtCore import QSignalBlocker


PROFILE_DIMENSION_MAXIMUM = 1_000_000.0
_PROPERTY_MAXIMUM = 1e30
_OPEN_PROFILES = {
    "I-profile",
    "H-profile",
    "C-profile",
    "Channel",
    "U-profile",
}


def apply_profile_parameter_limits(
    editors: Mapping,
    profile_type: str,
    dimensions: dict,
) -> None:
    """Apply profile ranges without emitting a competing refresh cascade."""
    for key, editor in editors.items():
        if key == "graph":
            continue
        minimum, maximum = profile_parameter_range(
            profile_type,
            key,
            dimensions,
        )
        blocker = QSignalBlocker(editor)
        editor.setRange(minimum, maximum)
        del blocker


def profile_parameter_range(
    profile_type: str,
    key: str,
    values: dict,
) -> tuple[float, float]:
    """Return a non-erroring editor range, including geometric thickness limits."""
    if profile_type == "General":
        minimum = -_PROPERTY_MAXIMUM if key == "iyz" else 0.0
        return minimum, _PROPERTY_MAXIMUM

    maximum = PROFILE_DIMENSION_MAXIMUM
    if key == "thickness" and profile_type == "Box":
        maximum = min(
            _non_negative(values, "width"),
            _non_negative(values, "height"),
        ) / 2.0
    elif key == "thickness" and profile_type == "Pipe":
        maximum = _non_negative(values, "diameter") / 2.0
    elif key == "web_thickness" and profile_type in _OPEN_PROFILES:
        maximum = _non_negative(values, "flange_width")
    elif key == "flange_thickness" and profile_type in _OPEN_PROFILES:
        maximum = _non_negative(values, "height") / 2.0
    return 0.0, min(maximum, PROFILE_DIMENSION_MAXIMUM)


def _non_negative(values: dict, key: str) -> float:
    """Read a dependent dimension defensively for an editor limit."""
    try:
        value = float(values.get(key, 0.0))
    except (TypeError, ValueError):
        return 0.0
    return max(value, 0.0) if math.isfinite(value) else 0.0
