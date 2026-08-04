"""Stores one completed topology optimization iteration."""

from dataclasses import dataclass, field

from ...core import Entity, register_model_type


@register_model_type("optimization_iteration")
@dataclass
class OptimizationIteration(Entity):
    """Persisted convergence and density metadata for one solver evaluation."""

    number: int = 0
    objective_value: float = 0.0
    constraint_values: dict[str, float] = field(default_factory=dict)
    maximum_density_change: float = 0.0
    solver_time: float = 0.0
    density_file: str = ""
    result_file: str = ""
    converged: bool = False
