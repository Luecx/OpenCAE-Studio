"""Defines one persistent execution record for an Analysis or Study."""

from dataclasses import dataclass, field
from typing import Any

from ...core import Entity, EntityRef, register_model_type
from .job_source_kind import JobSourceKind
from .job_status import JobStatus


@register_model_type("job")
@dataclass
class Job(Entity):
    """Persistent run identity shared by solver and study executions.

    The entity stores canonical lifecycle/source enums. Legacy serialized strings
    are accepted at construction and normalized immediately.
    """

    source_ref: EntityRef | None = None
    source_kind: JobSourceKind | str = JobSourceKind.ANALYSIS
    # Legacy field accepted from older project files. New files serialize only
    # ``source_ref`` so there is one canonical relationship.
    analysis_ref: EntityRef | None = field(
        default=None,
        metadata={"serialize": False},
    )
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
    result_refs: list[EntityRef] = field(default_factory=list)
    settings: dict[str, Any] = field(default_factory=dict)

    def __setattr__(self, name, value):
        """Normalize finite-domain fields at every mutation boundary."""
        if name == "status":
            value = JobStatus.coerce(value)
        elif name == "source_kind":
            value = JobSourceKind.coerce(value)
        super().__setattr__(name, value)

    def __post_init__(self) -> None:
        """Migrate legacy Analysis references and clamp persisted progress."""
        if self.source_ref is None and self.analysis_ref is not None:
            self.source_ref = self.analysis_ref
            self.source_kind = JobSourceKind.ANALYSIS

        if self.source_kind is JobSourceKind.ANALYSIS:
            self.analysis_ref = self.source_ref

        # Project files may contain progress produced by interrupted versions;
        # clamping keeps the persistent invariant independent of UI widgets.
        self.progress = min(max(float(self.progress), 0.0), 1.0)
        if self.exit_code is not None:
            self.exit_code = int(self.exit_code)

    @property
    def running(self) -> bool:
        """Return whether the Job is still considered active by the UI."""
        return self.status in {
            JobStatus.PREPARED,
            JobStatus.RUNNING,
            JobStatus.STOPPING,
        }

    def write_abaqus(self, writer, context) -> None:
        """Jobs do not contribute solver deck records."""
        return None

    def write_femaster(self, writer, context) -> None:
        """Jobs do not contribute solver deck records."""
        return None
