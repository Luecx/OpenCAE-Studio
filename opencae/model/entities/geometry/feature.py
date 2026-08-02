from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ...core import Entity, RegionMemberRef, register_model_type


@register_model_type("geometry_feature")
@dataclass
class GeometryFeature(Entity):
    feature_type: str = "Geometry Feature"
    references: list[RegionMemberRef | str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    status: str = "Current"
    suppressed: bool = False

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
