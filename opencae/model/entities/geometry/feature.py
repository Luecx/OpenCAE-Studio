from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from opencae.model.selection import RegionDefinition, as_region_definition

from ...core import Entity, register_model_type


@register_model_type("geometry_feature")
@dataclass
class GeometryFeature(Entity):
    feature_type: str = "Geometry Feature"
    target: RegionDefinition = field(default_factory=RegionDefinition)
    parameters: dict[str, Any] = field(default_factory=dict)
    status: str = "Current"
    suppressed: bool = False

    def __post_init__(self):
        self.target = as_region_definition(self.target)

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
