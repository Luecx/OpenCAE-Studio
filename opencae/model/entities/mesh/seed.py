from dataclasses import dataclass, field

from ...core import Entity, register_model_type
from opencae.model.selection import RegionDefinition, as_region_definition


@register_model_type("mesh_seed")
@dataclass
class Seed(Entity):
    seed_type: str = "Seed"
    method: str = "Size"
    size: float = 5.0
    divisions: int = 0
    bias: str = "None"
    bias_factor: float = 1.0
    target: RegionDefinition = field(default_factory=RegionDefinition)

    def __post_init__(self):
        self.target = as_region_definition(self.target)

    def write_abaqus(self, writer, context) -> None: return None
    def write_femaster(self, writer, context) -> None: return None
