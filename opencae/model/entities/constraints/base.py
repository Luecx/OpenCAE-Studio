from dataclasses import dataclass

from ...core import Entity, register_model_type
from .types import ConstraintType


@register_model_type("constraint")
@dataclass
class Constraint(Entity):
    constraint_type: ConstraintType | str = "Constraint"

    def __post_init__(self): self.constraint_type = ConstraintType.coerce(self.constraint_type)
    def write_abaqus(self, writer, context) -> None: return None
    def write_femaster(self, writer, context) -> None:
        return None
