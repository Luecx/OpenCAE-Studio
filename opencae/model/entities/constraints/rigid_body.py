from dataclasses import dataclass, field

from ...core import register_model_type
from .base import Constraint


@register_model_type("rigid_body_constraint")
@dataclass
class RigidBodyConstraint(Constraint):
    constraint_type: str = field(init=False, default="Rigid Body")

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        super().write_femaster(writer, context)
