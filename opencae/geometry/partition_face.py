from __future__ import annotations

from opencae.model.selection import local_geometry_tags

from .errors import GeometryError


def apply_face_partition(gmsh, part, feature):
    faces = sorted(local_geometry_tags(part, feature.target, 2))
    points = feature.points
    if len(faces)!=1:raise GeometryError('Face partition requires exactly one target face')
    if len(points)!=2:raise GeometryError('Face partition requires exactly two picked points')
    tags=[gmsh.model.occ.addPoint(*tuple(map(float,point))) for point in points]
    line=gmsh.model.occ.addLine(tags[0],tags[1])
    gmsh.model.occ.fragment([(2, faces[0])],[(1,line)],removeObject=True,removeTool=True); gmsh.model.occ.synchronize()
