"""Defines one scalar resource constraint for topology optimization."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ...core import Entity, register_model_type
from .constraint_operator import ConstraintOperator

if TYPE_CHECKING:
    from .optimization_response import OptimizationResponse


@register_model_type("optimization_constraint")
@dataclass
class OptimizationConstraint(Entity):
    """A response limit linked directly to an OptimizationResponse object."""

    response: OptimizationResponse | None = field(
        default=None,
        metadata={"reference_type": "OptimizationResponse"},
    )
    operator: ConstraintOperator | str = ConstraintOperator.LESS_EQUAL
    limit: float = 0.3
    active: bool = True

    def __post_init__(self):
        self.operator = ConstraintOperator(self.operator)
        self.limit = float(self.limit)
