"""Defines shared state for load entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ...core import Entity, register_model_type
from opencae.model.selection import RegionDefinition

if TYPE_CHECKING:
    from ..amplitudes import Amplitude
    from ..regions import CoordinateSystem


@register_model_type("load")
@dataclass
class Load(Entity):
    """Base load using object relationships for reusable resources."""

    load_type: str = "Load"
    target: RegionDefinition = field(default_factory=RegionDefinition)
    coordinate_system: CoordinateSystem | None = field(
        default=None,
        metadata={"reference_type": "CoordinateSystem"},
    )
    amplitude: Amplitude | None = field(
        default=None,
        metadata={"reference_type": "Amplitude"},
    )

    def __post_init__(self):
        from opencae.model.selection import as_region_definition
        self.target = as_region_definition(self.target)

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
