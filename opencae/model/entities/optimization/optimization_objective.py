"""Defines the response selected as the topology optimization objective."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ...core import Entity, register_model_type

if TYPE_CHECKING:
    from .optimization_response import OptimizationResponse


@register_model_type("optimization_objective")
@dataclass
class OptimizationObjective(Entity):
    """A minimize objective referencing one OptimizationResponse object."""

    response: OptimizationResponse | None = field(
        default=None,
        metadata={"reference_type": "OptimizationResponse"},
    )
    sense: str = "minimize"

    def __post_init__(self):
        self.sense = str(self.sense or "minimize").strip().lower()
        if self.sense != "minimize":
            raise ValueError(
                "The topology optimizer currently supports minimize objectives only"
            )
