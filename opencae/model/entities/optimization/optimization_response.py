"""Defines a region-scoped response evaluated during topology optimization."""

from dataclasses import dataclass, field

from opencae.model.selection import (
    RegionDefinition,
    RegionSelectionItem,
    WholeModelOperand,
)

from ...core import Entity, register_model_type
from .response_type import ResponseType


@register_model_type("optimization_response")
@dataclass
class OptimizationResponse(Entity):
    """A named response quantity and the element region on which it is evaluated."""

    response_type: ResponseType | str = ResponseType.STIFFNESS_ENERGY
    region: RegionDefinition = field(default_factory=RegionDefinition)

    def __post_init__(self):
        self.response_type = ResponseType(self.response_type)
        self.region = RegionDefinition.from_values(self.region)
        if self.region.empty:
            self.region = RegionDefinition(
                (RegionSelectionItem(WholeModelOperand()),)
            )
