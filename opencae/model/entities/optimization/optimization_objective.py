"""Defines the response selected as the topology optimization objective."""

from dataclasses import dataclass, field

from ...core import Entity, EntityRef, register_model_type


@register_model_type("optimization_objective")
@dataclass
class OptimizationObjective(Entity):
    """A minimize objective referencing one optimization response."""

    response_ref: EntityRef = field(
        default_factory=lambda: EntityRef(expected_type="OptimizationResponse")
    )
    sense: str = "minimize"

    def __post_init__(self):
        self.sense = str(self.sense or "minimize").strip().lower()
        if self.sense != "minimize":
            raise ValueError(
                "The topology optimizer currently supports minimize objectives only"
            )
