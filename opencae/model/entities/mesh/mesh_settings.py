from dataclasses import dataclass

from ...core import register_model_type


@register_model_type("mesh_settings")
@dataclass
class MeshSettings:
    algorithm_2d: str = "Frontal-Delaunay"
    algorithm_3d: str = "HXT"
    element_order: int = 1
    optimize: bool = True
    high_order_optimize: bool = True
    recombine_all: bool = False
    num_threads: int = 0
