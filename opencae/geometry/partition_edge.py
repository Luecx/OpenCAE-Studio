from __future__ import annotations

from .errors import GeometryError
from .labels import parse_labels


def apply_edge_partition(gmsh,feature):
    targets=parse_labels(feature.references,expected_dim=1)
    if len(targets)!=1:raise GeometryError('Edge partition requires exactly one target edge')
    edge=targets[0]; method=feature.parameters.get('method','Parameter')
    if method=='Vertex':
        vertices=parse_labels(feature.parameters.get('vertices',()),expected_dim=0)
        if len(vertices)!=1:raise GeometryError('Select exactly one splitting vertex')
        tool=vertices[0]
    else:
        fraction=float(feature.parameters.get('fraction',0.5))
        if not 0.0<fraction<1.0:raise GeometryError('Edge parameter must be between 0 and 1')
        lower,upper=gmsh.model.getParametrizationBounds(1,edge[1]); u=float(lower[0])+fraction*(float(upper[0])-float(lower[0])); xyz=gmsh.model.getValue(1,edge[1],[u]); tool=(0,gmsh.model.occ.addPoint(*xyz))
    gmsh.model.occ.fragment([edge],[tool],removeObject=True,removeTool=True); gmsh.model.occ.synchronize()
