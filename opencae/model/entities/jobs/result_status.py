"""Defines availability states for persisted result sets."""

from enum import StrEnum


class ResultStatus(StrEnum):
    """Canonical availability state of a ResultSet."""

    UNAVAILABLE = "Unavailable"
    AVAILABLE = "Available"

    @classmethod
    def coerce(cls, value) -> "ResultStatus":
        """Convert persisted text into a canonical ResultStatus."""
        if isinstance(value, cls):
            return value
        text = str(value or cls.UNAVAILABLE.value).strip()
        for status in cls:
            if status.value.casefold() == text.casefold():
                return status
        raise ValueError(f"Unknown Result status: {value!r}")
