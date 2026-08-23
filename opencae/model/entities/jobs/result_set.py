"""Defines one persisted solver or study result collection."""

from dataclasses import dataclass, field
from typing import Any

from ...core import Entity, EntityRef, register_model_type
from .result_field import ResultField
from .result_status import ResultStatus


@register_model_type("result_set")
@dataclass
class ResultSet(Entity):
    """Persistent result metadata linked to the Job that produced it."""

    job_ref: EntityRef | None = None
    source_file: str = ""
    status: ResultStatus | str = ResultStatus.UNAVAILABLE
    fields: list[ResultField] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __setattr__(self, name, value) -> None:
        """Normalize finite-domain result availability on assignment."""
        if name == "status":
            value = ResultStatus.coerce(value)
        super().__setattr__(name, value)

    def write_abaqus(self, writer, context) -> None:
        """Result metadata does not contribute solver deck records."""
        return None

    def write_femaster(self, writer, context) -> None:
        """Result metadata does not contribute solver deck records."""
        return None
