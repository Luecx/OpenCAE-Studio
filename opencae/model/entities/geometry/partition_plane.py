"""Defines plane-based geometry partition features."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ...core import register_model_type
from .feature import GeometryFeature

if TYPE_CHECKING:
    from ..datums import DatumPlane


@register_model_type("partition_plane_feature")
@dataclass
class PartitionPlaneFeature(GeometryFeature):
    feature_type: str = field(init=False, default="Partition by Plane")
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0)
    normal: tuple[float, float, float] = (1.0, 0.0, 0.0)
    datum_plane: DatumPlane | None = field(
        default=None,
        metadata={"reference_type": "DatumPlane"},
    )

    def __post_init__(self):
        super().__post_init__()
        self.origin = tuple(float(value) for value in self.origin)
        self.normal = tuple(float(value) for value in self.normal)
