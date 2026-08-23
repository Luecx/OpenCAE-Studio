"""Defines the finite lifecycle states of a Part mesh snapshot."""

from enum import StrEnum


class MeshStatus(StrEnum):
    """Canonical validity state for generated, imported, or authored mesh data."""

    NOT_GENERATED = "Not generated"
    AUTHORED = "Authored"
    CURRENT = "Current"
    OUTDATED = "Outdated"

    @classmethod
    def coerce(cls, value) -> "MeshStatus":
        """Convert persisted status text into a canonical MeshStatus."""
        if isinstance(value, cls):
            return value
        text = str(value or cls.NOT_GENERATED.value).strip()
        for status in cls:
            if status.value.casefold() == text.casefold():
                return status
        raise ValueError(f"Unknown mesh status: {value!r}")
