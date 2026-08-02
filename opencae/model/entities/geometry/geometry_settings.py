from dataclasses import dataclass

from ...core import register_model_type


@register_model_type("geometry_settings")
@dataclass
class GeometrySettings:
    heal_on_import: bool = True
    tolerance: float = 1.0e-7
    sew_faces: bool = True
    make_solids: bool = True
    remove_degenerate: bool = True
    display_size_factor: float = 0.025
