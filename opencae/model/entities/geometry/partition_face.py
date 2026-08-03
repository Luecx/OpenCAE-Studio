from dataclasses import dataclass, field

from ...core import register_model_type
from .feature import GeometryFeature


@register_model_type("partition_face_feature")
@dataclass
class PartitionFaceFeature(GeometryFeature):
    feature_type: str = field(init=False, default="Partition Face")
    points: tuple[tuple[float, float, float], ...] = field(default_factory=tuple)

    def __post_init__(self):
        super().__post_init__()
        self.points = tuple(tuple(float(component) for component in point) for point in self.points)
