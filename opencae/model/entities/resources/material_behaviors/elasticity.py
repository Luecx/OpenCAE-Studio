from dataclasses import dataclass, field
from ....core import register_model_type
from .base import MaterialBehavior

@register_model_type("isotropic_elasticity")
@dataclass
class IsotropicElasticity(MaterialBehavior):
    category: str = field(init=False, default="Elasticity")
    behavior_type: str = field(init=False, default="Isotropic elasticity")
    youngs_modulus: float = 210000.0
    poisson_ratio: float = 0.3

@register_model_type("neo_hooke_elasticity")
@dataclass
class NeoHookeElasticity(MaterialBehavior):
    category: str = field(init=False, default="Elasticity")
    behavior_type: str = field(init=False, default="Neo-Hooke")
    c10: float = 1.0
    d1: float = 0.0
