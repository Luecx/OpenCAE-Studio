from __future__ import annotations

from opencae.model.entities.geometry import (
    ImportedStepFeature,
    PartitionCellFeature,
    PartitionEdgeFeature,
    PartitionFaceFeature,
    PartitionPlaneFeature,
    SketchFeature,
)

from .errors import GeometryError
from .occ_import import import_source, source_feature
from .partition_edge import apply_edge_partition
from .partition_face import apply_face_partition
from .partition_plane import apply_plane_partition
from .sketch_feature import apply_sketch_feature


def rebuild_occ(gmsh, part) -> None:
    """Replay imported/authored Part geometry and downstream feature history."""
    imported = source_feature(part)
    if imported is not None:
        import_source(gmsh, part)
        imported.status = "Current"

    for feature in part.geometry:
        if feature.suppressed or isinstance(feature, ImportedStepFeature):
            continue
        try:
            if isinstance(feature, SketchFeature):
                apply_sketch_feature(gmsh, feature)
            elif isinstance(feature, (PartitionPlaneFeature, PartitionCellFeature)):
                apply_plane_partition(gmsh, part, feature)
            elif isinstance(feature, PartitionFaceFeature):
                apply_face_partition(gmsh, part, feature)
            elif isinstance(feature, PartitionEdgeFeature):
                apply_edge_partition(gmsh, part, feature)
            else:
                raise GeometryError(f"Unsupported history feature: {type(feature).__name__}")
            feature.status = "Current"
        except (GeometryError, RuntimeError, ValueError):
            feature.status = "Failed"
            raise

    if not part.geometry:
        raise GeometryError("The part has no geometry features")
    gmsh.model.occ.synchronize()
