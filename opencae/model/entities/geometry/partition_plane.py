from dataclasses import dataclass, field

from ...core import EntityRef, as_entity_ref, register_model_type
from .feature import GeometryFeature


@register_model_type("partition_plane_feature")
@dataclass
class PartitionPlaneFeature(GeometryFeature):
    feature_type: str = field(init=False, default="Partition by Plane")
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0)
    normal: tuple[float, float, float] = (1.0, 0.0, 0.0)
    datum_plane_ref: EntityRef | None = None

    def __post_init__(self):
        super().__post_init__()
        self.origin = tuple(float(value) for value in self.origin)
        self.normal = tuple(float(value) for value in self.normal)
        self.datum_plane_ref = as_entity_ref(self.datum_plane_ref, "DatumPlane") if self.datum_plane_ref else None
