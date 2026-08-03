from __future__ import annotations

from .errors import GeometryError
from opencae.model.selection import local_geometry_tags


def apply_edge_partition(gmsh, part, feature):
    targets = sorted(local_geometry_tags(part, feature.target, 1))
    if len(targets) != 1:
        raise GeometryError("Edge partition requires exactly one target edge")
    edge = (1, targets[0])
    method = feature.method
    if method=='Vertex':
        vertices = sorted(local_geometry_tags(part, feature.split_target, 0))
        if len(vertices) != 1:
            raise GeometryError("Select exactly one splitting vertex")
        tool = (0, vertices[0])
    else:
        fraction=float(feature.fraction)
        if not 0.0<fraction<1.0:raise GeometryError('Edge parameter must be between 0 and 1')
        lower,upper=gmsh.model.getParametrizationBounds(1,edge[1]); u=float(lower[0])+fraction*(float(upper[0])-float(lower[0])); xyz=gmsh.model.getValue(1,edge[1],[u]); tool=(0,gmsh.model.occ.addPoint(*xyz))
    gmsh.model.occ.fragment([edge],[tool],removeObject=True,removeTool=True); gmsh.model.occ.synchronize()
