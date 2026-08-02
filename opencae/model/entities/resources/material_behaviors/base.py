from dataclasses import dataclass
from ....core import SolverWritable, register_model_type

@register_model_type("material_behavior")
@dataclass
class MaterialBehavior(SolverWritable):
    category: str = "Property"
    behavior_type: str = "Generic"
