from dataclasses import dataclass, field
from ...core import register_model_type
from .base import Load


@register_model_type("inertia_load")
@dataclass
class InertiaLoad(Load):
    load_type: str = field(init=False, default="Inertia Load")
    center: tuple[float, float, float] = (0.0, 0.0, 0.0)
    center_acceleration: tuple[float, float, float] = (0.0, 0.0, 0.0)
    angular_velocity: tuple[float, float, float] = (0.0, 0.0, 0.0)
    angular_acceleration: tuple[float, float, float] = (0.0, 0.0, 0.0)
    consider_point_masses: bool = False
