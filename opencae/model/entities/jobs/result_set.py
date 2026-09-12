"""Defines one persisted solver or study result collection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ...core import Entity, register_model_type
from .result_field import ResultField
from .result_status import ResultStatus

if TYPE_CHECKING:
    from .job import Job


@register_model_type("result_set")
@dataclass
class ResultSet(Entity):
    """Persistent result metadata linked directly to the producing Job object."""

    job: Job | None = field(
        default=None,
        metadata={"reference_type": "Job"},
    )
    source_file: str = ""
    status: ResultStatus | str = ResultStatus.UNAVAILABLE
    fields: list[ResultField] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __setattr__(self, name, value) -> None:
        if name == "status":
            value = ResultStatus.coerce(value)
        super().__setattr__(name, value)

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
