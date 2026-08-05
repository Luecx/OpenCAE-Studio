"""Stores topology-specific state for one job-backed study execution."""

from dataclasses import dataclass, field

from ...core import Entity, EntityRef, register_model_type
from .optimization_iteration import OptimizationIteration


@register_model_type("optimization_run")
@dataclass
class OptimizationRun(Entity):
    """Persistent topology state linked to the generic job that produced it."""

    optimization_ref: EntityRef = field(
        default_factory=lambda: EntityRef(expected_type="TopologyOptimization")
    )
    job_ref: EntityRef | None = None
    status: str = "Prepared"
    directory: str = ""
    mesh_fingerprint: str = ""
    density_constraint_radius: float = 0.0
    sensitivity_radius: float = 0.0
    iterations: list[OptimizationIteration] = field(default_factory=list)
    message: str = ""
