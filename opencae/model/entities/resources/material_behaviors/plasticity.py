from dataclasses import dataclass, field
from ....core import register_model_type
from .base import MaterialBehavior

@register_model_type("isotropic_plasticity")
@dataclass
class IsotropicPlasticity(MaterialBehavior):
    category: str = field(init=False, default="Plasticity")
    behavior_type: str = field(init=False, default="Bilinear isotropic hardening")
    yield_stress: float = 250.0
    tangent_modulus: float = 0.0
