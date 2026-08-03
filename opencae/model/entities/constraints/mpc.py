from dataclasses import dataclass, field

from ...core import register_model_type
from opencae.model.selection import RegionDefinition, as_region_definition
from .base import Constraint


@register_model_type("mpc_constraint")
@dataclass
class MPCConstraint(Constraint):
    constraint_type: str = field(init=False, default="MPC")
    master: RegionDefinition = field(default_factory=RegionDefinition)
    slave: RegionDefinition = field(default_factory=RegionDefinition)

    def __post_init__(self): super().__post_init__(); self.master = as_region_definition(self.master); self.slave = as_region_definition(self.slave)
