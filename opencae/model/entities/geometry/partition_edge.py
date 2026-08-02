from dataclasses import dataclass, field

from ...core import register_model_type
from .feature import GeometryFeature


@register_model_type("partition_edge_feature")
@dataclass
class PartitionEdgeFeature(GeometryFeature):
    feature_type: str = field(init=False, default="Partition Edge")

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
