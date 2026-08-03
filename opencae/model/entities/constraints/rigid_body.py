from dataclasses import dataclass, field

from ...core import register_model_type
from opencae.model.selection import RegionDefinition, as_region_definition
from .base import Constraint


@register_model_type("rigid_body_constraint")
@dataclass
class RigidBodyConstraint(Constraint):
    constraint_type: str = field(init=False, default="Rigid Body")
    reference: RegionDefinition = field(default_factory=RegionDefinition)
    body: RegionDefinition = field(default_factory=RegionDefinition)

    def __post_init__(self):
        super().__post_init__(); self.reference = as_region_definition(self.reference); self.body = as_region_definition(self.body)

    @property
    def master(self): return self.reference
    @master.setter
    def master(self, value): self.reference = as_region_definition(value)
    @property
    def slave(self): return self.body
    @slave.setter
    def slave(self, value): self.body = as_region_definition(value)
