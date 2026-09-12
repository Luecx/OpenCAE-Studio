"""Defines support boundary-condition domain entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ...core import Entity, register_model_type
from opencae.model.selection import RegionDefinition, as_region_definition

if TYPE_CHECKING:
    from ..regions import CoordinateSystem


@register_model_type("support")
@dataclass
class Support(Entity):
    support_type: str = "Support"
    target: RegionDefinition = field(default_factory=RegionDefinition)
    coordinate_system: CoordinateSystem | None = field(
        default=None,
        metadata={"reference_type": "CoordinateSystem"},
    )
    components: list[float | None] = field(default_factory=lambda: [None] * 6)

    def __post_init__(self):
        self.target = as_region_definition(self.target)

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
