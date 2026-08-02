from dataclasses import dataclass, field

from ...core import register_model_type
from .feature import GeometryFeature


@register_model_type("partition_cell_feature")
@dataclass
class PartitionCellFeature(GeometryFeature):
    feature_type: str = field(init=False, default="Partition Cell")

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
