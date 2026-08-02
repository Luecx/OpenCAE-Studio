from dataclasses import dataclass, field
from ....core import register_model_type
from .base import MaterialBehavior

@register_model_type("density_behavior")
@dataclass
class DensityBehavior(MaterialBehavior):
    category: str = field(init=False, default="Density")
    behavior_type: str = field(init=False, default="Constant density")
    value: float = 0.0
