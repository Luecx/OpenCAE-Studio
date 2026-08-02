from __future__ import annotations

from .errors import GeometryError
from .labels import parse_labels


def apply_face_partition(gmsh,feature):
    faces=parse_labels(feature.references,expected_dim=2); points=feature.parameters.get('points',())
    if len(faces)!=1:raise GeometryError('Face partition requires exactly one target face')
    if len(points)!=2:raise GeometryError('Face partition requires exactly two picked points')
    tags=[gmsh.model.occ.addPoint(*tuple(map(float,point))) for point in points]
    line=gmsh.model.occ.addLine(tags[0],tags[1])
    gmsh.model.occ.fragment([faces[0]],[(1,line)],removeObject=True,removeTool=True); gmsh.model.occ.synchronize()
