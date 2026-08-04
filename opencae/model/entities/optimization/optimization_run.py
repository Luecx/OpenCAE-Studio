"""Stores one topology optimization run and its completed iterations."""

from dataclasses import dataclass, field

from ...core import Entity, EntityRef, register_model_type
from .optimization_iteration import OptimizationIteration


@register_model_type("optimization_run")
@dataclass
class OptimizationRun(Entity):
    """Persistent run status, resolved filter radii and iteration history."""

    optimization_ref: EntityRef = field(
        default_factory=lambda: EntityRef(expected_type="TopologyOptimization")
    )
    status: str = "Prepared"
    directory: str = ""
    mesh_fingerprint: str = ""
    density_constraint_radius: float = 0.0
    sensitivity_radius: float = 0.0
    iterations: list[OptimizationIteration] = field(default_factory=list)
    message: str = ""
