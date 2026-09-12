"""Defines the finite value shapes exposed by field definitions."""

from enum import StrEnum


class FieldValueKind(StrEnum):
    """Identify whether field rows represent scalars, vectors, or custom tuples."""

    SCALAR = "Scalar"
    VECTOR = "Vector"
    CUSTOM = "Custom"

    @classmethod
    def coerce(cls, value) -> "FieldValueKind":
        """Normalize persisted or UI value-shape text to a canonical member."""
        if isinstance(value, cls):
            return value
        text = str(value or cls.SCALAR.value).strip()
        for kind in cls:
            if kind.value.casefold() == text.casefold():
                return kind
        raise ValueError(f"Unknown field value kind: {value!r}")
