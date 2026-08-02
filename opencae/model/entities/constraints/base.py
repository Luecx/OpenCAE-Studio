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
    components: tuple[int, int, int, int, int, int] = (1, 1, 1, 1, 1, 1)
    adjust: bool | None = None
    distance: float | None = None
    parameters: dict[str, object] = field(default_factory=dict)

    def __post_init__(self):
        self.constraint_type = ConstraintType.coerce(self.constraint_type)
        self.master = as_reference(self.master, ConstraintReferenceKind.REFERENCE_POINT)
        slave_kind = self.parameters.pop("slave_type", ConstraintReferenceKind.UNKNOWN)
        self.slave = as_reference(self.slave, slave_kind)
        if "components" in self.parameters: self.components = tuple(int(value) for value in self.parameters.pop("components"))
        if "adjust" in self.parameters and self.adjust is None: self.adjust = bool(self.parameters.pop("adjust"))
        if "distance" in self.parameters and self.distance is None: self.distance = float(self.parameters.pop("distance"))

    @property
    def master_ref(self): return self.master.ref
    @property
    def slave_ref(self): return self.slave.ref

    def write_abaqus(self, writer, context) -> None: return None
    def write_femaster(self, writer, context) -> None:
        from opencae.solvers.femaster_dsl.emitters.constraints import write_constraint
        write_constraint(self, writer, context)
