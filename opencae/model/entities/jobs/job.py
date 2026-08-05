"""Defines one concrete execution of an Analysis or Study."""

from dataclasses import dataclass, field
from typing import Any

from ...core import Entity, EntityRef, register_model_type


@register_model_type("job")
@dataclass
class Job(Entity):
    """Persistent run identity shared by solver and study executions."""

    source_ref: EntityRef | None = None
    source_kind: str = "analysis"
    # Legacy field accepted from older project files.
    analysis_ref: EntityRef | None = field(
        default=None,
        metadata={"serialize": False},
    )
    solver: str = "FEMaster"
    status: str = "Prepared"
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

    def __post_init__(self):
        if self.source_ref is None and self.analysis_ref is not None:
            self.source_ref = self.analysis_ref
            self.source_kind = "analysis"
        if self.source_kind == "analysis":
            self.analysis_ref = self.source_ref
        self.source_kind = str(self.source_kind or "analysis").strip().lower()
        self.progress = min(max(float(self.progress), 0.0), 1.0)

    @property
    def running(self) -> bool:
        return self.status.casefold() in {"prepared", "running", "stopping"}

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
