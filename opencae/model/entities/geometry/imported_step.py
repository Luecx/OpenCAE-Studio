from dataclasses import dataclass, field

from ...core import register_model_type
from .feature import GeometryFeature


@register_model_type("imported_step_feature")
@dataclass
class ImportedStepFeature(GeometryFeature):
    feature_type: str = field(init=False, default="Imported OCC Geometry")

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
