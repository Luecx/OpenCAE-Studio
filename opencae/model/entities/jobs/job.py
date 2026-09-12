"""Defines one persistent execution record for an Analysis or Study."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ...core import Entity, register_model_type
from .job_source_kind import JobSourceKind
from .job_status import JobStatus

if TYPE_CHECKING:
    from ..analysis import Analysis
    from ..studies import Study
    from .result_set import ResultSet


@register_model_type("job")
@dataclass
class Job(Entity):
    """Persistent run identity with direct source/result object relationships."""

    source: Analysis | Study | None = field(
        default=None,
        metadata={"reference_type": "Analysis|Study"},
    )
    source_kind: JobSourceKind | str = JobSourceKind.ANALYSIS
    solver: str = "FEMaster"
    status: JobStatus | str = JobStatus.PREPARED
    exit_code: int | None = None
    created_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    directory: str = ""
    input_deck: str = ""
    output_file: str = ""
    progress: float = 0.0
    progress_label: str = "Prepared"
    results: list[ResultSet] = field(
        default_factory=list,
        metadata={"reference_type": "ResultSet"},
    )
    settings: dict[str, Any] = field(default_factory=dict)

    def __setattr__(self, name, value):
        if name == "status":
            value = JobStatus.coerce(value)
        elif name == "source_kind":
            value = JobSourceKind.coerce(value)
        super().__setattr__(name, value)

    def __post_init__(self) -> None:
        self.progress = min(max(float(self.progress), 0.0), 1.0)
        if self.exit_code is not None:
            self.exit_code = int(self.exit_code)

    @property
    def running(self) -> bool:
        return self.status in {
            JobStatus.PREPARED,
            JobStatus.RUNNING,
            JobStatus.STOPPING,
        }

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
