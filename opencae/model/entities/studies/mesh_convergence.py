"""Persistent, solver-independent mesh-refinement Study definition."""
from dataclasses import dataclass, field

from opencae.model.core import EntityRef, register_model_type
from .study import Study


@register_model_type("mesh_convergence_study")
@dataclass
class MeshConvergenceStudy(Study):
    study_type: str = field(init=False, default="Mesh Convergence")
    analysis_ref: EntityRef = field(
        default_factory=lambda: EntityRef(expected_type="Analysis"),
        metadata={"reference_type": "Analysis"},
    )
    mesh_scales: list[float] = field(default_factory=lambda: [1.0, 0.7, 0.5, 0.35])  # Legacy project compatibility
    mesh_scaling_factor: float = 0.7
    max_iterations: int = 4
    field_name: str = "DISP"
    component: str = "Magnitude"
    step_id: int = 1
    metric: str = "probe"
    # Independently named convergence controls. Each selected node is stored
    # with its original spatial position: solver node numbering changes on remesh.
    metrics: list[dict] = field(default_factory=list)
    probe_position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    exclude_center: tuple[float, float, float] = (0.0, 0.0, 0.0)
    exclude_radius: float = 0.0
    relative_tolerance: float = 0.02
    # Each entry includes the original FRD file path, element count, scalar,
    # and diagnostic. A new run appends a self-contained record of its samples.
    run_history: list[dict] = field(default_factory=list)
