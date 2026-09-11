"""Defines the finite input-source kinds supported by field definitions."""

from enum import StrEnum


class FieldSourceKind(StrEnum):
    """Identify how field values enter the model."""

    TABULAR = "Tabular"
    FORMULA = "Formula"
    FILE = "File"

    @classmethod
    def coerce(cls, value) -> "FieldSourceKind":
        """Normalize persisted or UI source text to a canonical member."""
        if isinstance(value, cls):
            return value
        text = str(value or cls.FORMULA.value).strip()
        for kind in cls:
            if kind.value.casefold() == text.casefold():
                return kind
        raise ValueError(f"Unknown field source kind: {value!r}")
