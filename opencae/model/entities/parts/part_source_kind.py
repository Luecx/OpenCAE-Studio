"""Defines the finite origins from which a Part can be created."""

from enum import StrEnum


class PartSourceKind(StrEnum):
    """Identify whether a Part is authored, CAD-backed, or an orphan mesh."""

    MANUAL = "Manual"
    CAD = "CAD"
    ORPHAN_MESH = "Orphan Mesh"

    @classmethod
    def coerce(cls, value) -> "PartSourceKind":
        """Normalize API and persisted source labels to a canonical member."""
        if isinstance(value, cls):
            return value
        text = str(value or cls.MANUAL.value).strip()
        for kind in cls:
            if kind.value.casefold() == text.casefold():
                return kind
        raise ValueError(f"Unknown part source kind: {value!r}")
