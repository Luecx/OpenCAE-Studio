from __future__ import annotations

from opencae.model.entities.geometry import (
    ImportedStepFeature,
    PartitionCellFeature,
    PartitionEdgeFeature,
    PartitionFaceFeature,
    PartitionPlaneFeature,
)

from .errors import GeometryError
from .occ_import import import_source
from .partition_edge import apply_edge_partition
from .partition_face import apply_face_partition
from .partition_plane import apply_plane_partition


def rebuild_occ(gmsh, part) -> None:
    import_source(gmsh, part)
    for feature in part.geometry:
        if feature.suppressed or isinstance(feature, ImportedStepFeature):
            continue
        try:
            if isinstance(feature, (PartitionPlaneFeature, PartitionCellFeature)):
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
    gmsh.model.occ.synchronize()
