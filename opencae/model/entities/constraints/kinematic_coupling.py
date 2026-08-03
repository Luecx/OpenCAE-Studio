from dataclasses import dataclass, field

from ...core import register_model_type
from opencae.model.selection import RegionDefinition, as_region_definition
from .base import Constraint


@register_model_type("kinematic_coupling")
@dataclass
class KinematicCoupling(Constraint):
    constraint_type: str = field(init=False, default="Kinematic Coupling")
    control_point: RegionDefinition = field(default_factory=RegionDefinition)
    slave: RegionDefinition = field(default_factory=RegionDefinition)
    components: tuple[int, int, int, int, int, int] = (1, 1, 1, 1, 1, 1)

    def __post_init__(self):
        super().__post_init__(); self.control_point = as_region_definition(self.control_point); self.slave = as_region_definition(self.slave)

    @property
    def master(self): return self.control_point
    @master.setter
    def master(self, value): self.control_point = as_region_definition(value)
