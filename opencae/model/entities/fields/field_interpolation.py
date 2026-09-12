"""Defines interpolation methods available to file-backed fields."""

from enum import StrEnum


class FieldInterpolation(StrEnum):
    """Identify how file samples are evaluated away from source coordinates."""

    NEAREST = "Nearest"
    LINEAR = "Linear"
    CUBIC = "Cubic"

    @classmethod
    def coerce(cls, value) -> "FieldInterpolation":
        """Normalize persisted or UI interpolation text to a canonical member."""
        if isinstance(value, cls):
            return value
        text = str(value or cls.LINEAR.value).strip()
        for interpolation in cls:
            if interpolation.value.casefold() == text.casefold():
                return interpolation
        raise ValueError(f"Unknown field interpolation: {value!r}")
