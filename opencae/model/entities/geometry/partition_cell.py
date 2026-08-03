from dataclasses import dataclass, field

from ...core import register_model_type
from .partition_plane import PartitionPlaneFeature


@register_model_type("partition_cell_feature")
@dataclass
class PartitionCellFeature(PartitionPlaneFeature):
    feature_type: str = field(init=False, default="Partition Cell")
