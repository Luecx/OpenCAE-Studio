"""Defines the finite source kinds that may own a persistent Job."""

from enum import StrEnum


class JobSourceKind(StrEnum):
    """Identifies which executable domain object produced a Job."""

    ANALYSIS = "analysis"
    STUDY = "study"

    @classmethod
    def coerce(cls, value) -> "JobSourceKind":
        """Convert persisted source-kind text into a canonical value."""
        if isinstance(value, cls):
            return value
        text = str(value or cls.ANALYSIS.value).strip().casefold()
        try:
            return cls(text)
        except ValueError as exc:
            raise ValueError(f"Unknown Job source kind: {value!r}") from exc
