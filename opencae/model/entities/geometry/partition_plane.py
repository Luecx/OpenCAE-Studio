from dataclasses import dataclass, field

from ...core import register_model_type
from .feature import GeometryFeature


@register_model_type("partition_plane_feature")
@dataclass
class PartitionPlaneFeature(GeometryFeature):
    feature_type: str = field(init=False, default="Partition by Plane")

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
