from .feature import GeometryFeature
from .geometry_settings import GeometrySettings
from .imported_step import ImportedStepFeature
from .partition_cell import PartitionCellFeature
from .partition_edge import PartitionEdgeFeature
from .partition_face import PartitionFaceFeature
from .partition_plane import PartitionPlaneFeature
from .sketch import (
    SKETCH_ENTITY_TYPES,
    SketchArc,
    SketchAxis,
    SketchBooleanOperation,
    SketchCircle,
    SketchConstraint,
    SketchConstraintKind,
    SketchDefinition,
    SketchEllipse,
    SketchEntity,
    SketchFeature,
    SketchFeatureMode,
    SketchLine,
    SketchObject,
    SketchPoint,
    SketchReference,
    SketchSpline,
    entity_points,
)

# Direct object identities are local to one owned sketch graph. This lets a
# duplicated Part retain local sketch IDs without creating project-wide identity
# collisions while preserving exact shared-point identity inside each sketch.
SketchDefinition.__model_identity_scope__ = True

__all__ = [
    "GeometryFeature", "GeometrySettings", "ImportedStepFeature",
    "PartitionCellFeature", "PartitionEdgeFeature", "PartitionFaceFeature",
    "PartitionPlaneFeature", "SketchObject", "SketchPoint", "SketchLine",
    "SketchCircle", "SketchArc", "SketchEllipse", "SketchSpline",
    "SketchEntity", "SketchReference", "SketchConstraintKind",
    "SketchConstraint", "SketchDefinition", "SketchFeatureMode",
    "SketchBooleanOperation", "SketchAxis", "SketchFeature",
    "SKETCH_ENTITY_TYPES", "entity_points",
]
