from dataclasses import dataclass, field
from ....core import register_model_type
from .base import MaterialBehavior

@register_model_type("isotropic_thermal_expansion")
@dataclass
class IsotropicThermalExpansion(MaterialBehavior):
    category: str = field(init=False, default="Thermal expansion")
    behavior_type: str = field(init=False, default="Isotropic expansion")
    coefficient: float = 0.0
    reference_temperature: float = 20.0
