"""Stores topology-specific state for one Job-backed study execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ...core import Entity, register_model_type
from ..jobs.job_status import JobStatus
from .optimization_iteration import OptimizationIteration

if TYPE_CHECKING:
    from ..jobs import Job
    from .topology_optimization import TopologyOptimization


@register_model_type("optimization_run")
@dataclass
class OptimizationRun(Entity):
    """Persistent topology state linked directly to its Study and Job objects."""

    optimization: TopologyOptimization | None = field(
        default=None,
        metadata={"reference_type": "TopologyOptimization"},
    )
    job: Job | None = field(
        default=None,
        metadata={"reference_type": "Job"},
    )
    status: JobStatus | str = JobStatus.PREPARED
    directory: str = ""
    mesh_fingerprint: str = ""
    density_constraint_radius: float = 0.0
    sensitivity_radius: float = 0.0
    iterations: list[OptimizationIteration] = field(default_factory=list)
    message: str = ""

    def __setattr__(self, name, value) -> None:
        if name == "status":
            value = JobStatus.coerce(value)
        super().__setattr__(name, value)
