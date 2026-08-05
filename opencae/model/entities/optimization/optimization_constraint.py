"""Defines one scalar resource constraint for topology optimization."""

from dataclasses import dataclass, field

from ...core import Entity, EntityRef, register_model_type
from .constraint_operator import ConstraintOperator


@register_model_type("optimization_constraint")
@dataclass
class OptimizationConstraint(Entity):
    """A response limit consumed by the OC and bisection update."""

    response_ref: EntityRef = field(
        default_factory=lambda: EntityRef(expected_type="OptimizationResponse")
    )
    operator: ConstraintOperator | str = ConstraintOperator.LESS_EQUAL
    limit: float = 0.3
    active: bool = True

    def __post_init__(self):
        self.operator = ConstraintOperator(self.operator)
        self.limit = float(self.limit)
