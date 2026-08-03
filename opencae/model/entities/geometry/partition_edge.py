from dataclasses import dataclass, field

from opencae.model.selection import RegionDefinition, as_region_definition

from ...core import register_model_type
from .feature import GeometryFeature


@register_model_type("partition_edge_feature")
@dataclass
class PartitionEdgeFeature(GeometryFeature):
    feature_type: str = field(init=False, default="Partition Edge")
    method: str = "Parameter"
    fraction: float = 0.5
    split_target: RegionDefinition = field(default_factory=RegionDefinition)

    def __post_init__(self):
        super().__post_init__()
        self.method = str(self.method or "Parameter")
        self.fraction = float(self.fraction)
        self.split_target = as_region_definition(self.split_target)
