"""Defines the finite spatial locations supported by field definitions."""

from enum import StrEnum


class FieldLocation(StrEnum):
    """Identify where each row of field values is evaluated or stored."""

    NODAL = "Nodal"
    ELEMENT = "Element"
    ELEMENT_NODAL = "Element-Nodal"
    INTEGRATION_POINT = "Integration Point"
    MATERIAL_POINT = "Material Point"
    SHELL_NORMAL = "Shell Normal"

    @classmethod
    def coerce(cls, value) -> "FieldLocation":
        """Normalize persisted or UI location text to a canonical member."""
        if isinstance(value, cls):
            return value
        text = str(value or cls.NODAL.value).strip()
        for location in cls:
            if location.value.casefold() == text.casefold():
                return location
        raise ValueError(f"Unknown field location: {value!r}")
