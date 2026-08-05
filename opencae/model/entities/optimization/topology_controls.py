"""Stores numerical controls for the topology optimization loop."""

from dataclasses import dataclass

from ...core import Entity, register_model_type


@register_model_type("topology_controls")
@dataclass
class TopologyControls(Entity):
    """Iteration, convergence, SIMP and file-retention controls."""

    name: str = "Optimization Controls"
    maximum_iterations: int = 100
    minimum_density: float = 1.0e-3
    initial_density: float = 0.5
    simp_exponent: float = 3.0
    move_limit: float = 0.20
    density_change_tolerance: float = 5.0e-3
    objective_tolerance: float = 1.0e-3
    bisection_tolerance: float = 1.0e-8
    maximum_bisection_steps: int = 100
    save_every: int = 1
    keep_solver_files: bool = False
