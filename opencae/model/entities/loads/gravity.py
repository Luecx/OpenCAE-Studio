from dataclasses import dataclass, field

from ...core import register_model_type
from .base import Load


@register_model_type("gravity_load")
@dataclass
class GravityLoad(Load):
    load_type: str = field(init=False, default="Gravity")
    magnitude: float = 0.0
    direction: str = "Global Z"
