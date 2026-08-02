from dataclasses import dataclass, field

from ...core import register_model_type
from .feature import GeometryFeature


@register_model_type("partition_face_feature")
@dataclass
class PartitionFaceFeature(GeometryFeature):
    feature_type: str = field(init=False, default="Partition Face")

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
