"""Defines the provenance of individual nodes and finite elements."""

from enum import StrEnum


class MeshEntityOrigin(StrEnum):
    """Identify how one node or element entered a Part mesh."""

    GENERATED = "generated"
    IMPORTED = "imported"
    AUTHORED = "authored"

    @classmethod
    def coerce(cls, value) -> "MeshEntityOrigin":
        """Normalize persisted provenance text to a canonical member."""
        if isinstance(value, cls):
            return value
        text = str(value or cls.GENERATED.value).strip().casefold()
        try:
            return cls(text)
        except ValueError as exc:
            raise ValueError(f"Unknown mesh entity origin: {value!r}") from exc
