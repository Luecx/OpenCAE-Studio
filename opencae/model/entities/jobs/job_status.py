"""Defines the finite lifecycle states allowed for persistent Jobs."""

from enum import StrEnum


class JobStatus(StrEnum):
    """Canonical lifecycle state for Analysis and Study executions."""

    PREPARED = "Prepared"
    RUNNING = "Running"
    STOPPING = "Stopping"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    FAILED = "Failed"

    @classmethod
    def coerce(cls, value) -> "JobStatus":
        """Convert persisted/legacy status text into a canonical JobStatus."""
        if isinstance(value, cls):
            return value
        text = str(value or cls.PREPARED.value).strip()
        # Older project files encoded solver codes inside the status string.
        if text.casefold().startswith("failed"):
            return cls.FAILED
        for status in cls:
            if status.value.casefold() == text.casefold():
                return status
        raise ValueError(f"Unknown Job status: {value!r}")
