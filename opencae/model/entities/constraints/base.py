from dataclasses import dataclass, field

from ...core import Entity, register_model_type
from .reference import ConstraintReference, as_reference
from .types import ConstraintReferenceKind, ConstraintType


@register_model_type("constraint")
@dataclass
class Constraint(Entity):
    constraint_type: ConstraintType | str = "Constraint"
    master: ConstraintReference | str = field(default_factory=ConstraintReference)
    slave: ConstraintReference | str = field(default_factory=ConstraintReference)
    parameters: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        self.constraint_type = ConstraintType.coerce(self.constraint_type)
        self.master = as_reference(self.master, ConstraintReferenceKind.REFERENCE_POINT)
        slave_kind = self.parameters.get("slave_type", ConstraintReferenceKind.UNKNOWN)
        self.slave = as_reference(self.slave, slave_kind)

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        from opencae.solvers.femaster_dsl.emitters.constraints import write_constraint
        write_constraint(self, writer, context)
