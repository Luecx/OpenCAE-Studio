from dataclasses import dataclass, field

from ...core import register_model_type
from .feature import GeometryFeature


@register_model_type("imported_step_feature")
@dataclass
class ImportedStepFeature(GeometryFeature):
    feature_type: str = field(init=False, default="Imported OCC Geometry")
    source_file: str = ""

    def __post_init__(self):
        super().__post_init__()
        self.source_file = str(self.source_file or "")
