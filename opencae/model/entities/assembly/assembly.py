from dataclasses import dataclass, field

from ...core import Entity, register_model_type
from ..constraints.base import Constraint
from ..regions.coordinate_system import CoordinateSystem
from ..regions.reference_point import ReferencePoint
from ..regions.region import Region
from .instance import Instance


@register_model_type("assembly")
@dataclass
class Assembly(Entity):
    instances: list[Instance] = field(default_factory=list)
    regions: list[Region] = field(default_factory=list)
    coordinate_systems: list[CoordinateSystem] = field(default_factory=list)
    reference_points: list[ReferencePoint] = field(default_factory=list)
    constraints: list[Constraint] = field(default_factory=list)

    def write_abaqus(self, writer, context) -> None:
        for instance in self.instances:
            instance.write_abaqus(writer, context)
        for constraint in self.constraints:
            constraint.write_abaqus(writer, context)

    def write_femaster(self, writer, context) -> None:
        for instance in self.instances:
            instance.write_femaster(writer, context)
        for constraint in self.constraints:
            constraint.write_femaster(writer, context)
