from __future__ import annotations
from .errors import GeometryError
from .occ_import import import_source
from .partition_edge import apply_edge_partition
from .partition_face import apply_face_partition
from .partition_plane import apply_plane_partition


def rebuild_occ(gmsh,part)->None:
    import_source(gmsh,part)
    for feature in part.geometry:
        if feature.suppressed or feature.feature_type.startswith('Imported'):continue
        try:
            if feature.feature_type in {'Partition by Plane','Partition Cell'}:apply_plane_partition(gmsh,feature)
            elif feature.feature_type=='Partition Face':apply_face_partition(gmsh,feature)
            elif feature.feature_type=='Partition Edge':apply_edge_partition(gmsh,feature)
            else:raise GeometryError(f'Unsupported history feature: {feature.feature_type}')
            feature.status='Current'
        except Exception:
            feature.status='Failed'; raise
    gmsh.model.occ.synchronize()
