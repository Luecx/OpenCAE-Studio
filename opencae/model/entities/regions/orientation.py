"""Defines material Orientation relationships for Part regions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ...core import Entity, register_model_type

if TYPE_CHECKING:
    from .coordinate_system import CoordinateSystem
    from .region import Region


@register_model_type("orientation")
@dataclass
class Orientation(Entity):
    region: Region | None = field(
        default=None,
        metadata={"reference_type": "Region"},
    )
    coordinate_system: CoordinateSystem | None = field(
        default=None,
        metadata={"reference_type": "CoordinateSystem"},
    )
    orientation_type: str = "Material"

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
