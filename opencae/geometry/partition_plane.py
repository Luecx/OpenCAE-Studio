from __future__ import annotations

import math

from opencae.model.selection import local_geometry_tags

from .errors import GeometryError


def apply_plane_partition(gmsh, part, feature) -> None:
    origin = tuple(float(v) for v in feature.origin)
    normal = _normalized(tuple(float(v) for v in feature.normal))
    target_tags = sorted(local_geometry_tags(part, feature.target, 3))
    objects = [(3, tag) for tag in target_tags] or list(gmsh.model.getEntities(3))
    if not objects:
        raise GeometryError("Plane partition requires at least one solid cell")
    size = _model_size(gmsh, objects) * 1.5
    plane = _add_plane(gmsh, origin, normal, size)
    gmsh.model.occ.fragment(objects, [(2, plane)], removeObject=True, removeTool=True)
    gmsh.model.occ.synchronize()


def _normalized(vector):
    length = math.sqrt(sum(value * value for value in vector))
    if length <= 1.0e-14:
        raise GeometryError("Partition plane normal must not be zero")
    return tuple(value / length for value in vector)


def _model_size(gmsh, objects):
    boxes = [gmsh.model.getBoundingBox(dim, tag) for dim, tag in objects]
    xmin = min(box[0] for box in boxes); ymin = min(box[1] for box in boxes); zmin = min(box[2] for box in boxes)
    xmax = max(box[3] for box in boxes); ymax = max(box[4] for box in boxes); zmax = max(box[5] for box in boxes)
    diagonal = math.sqrt((xmax-xmin)**2 + (ymax-ymin)**2 + (zmax-zmin)**2)
    return max(diagonal, 1.0)


def _add_plane(gmsh, origin, normal, size):
    reference = (0.0, 0.0, 1.0) if abs(normal[2]) < 0.9 else (0.0, 1.0, 0.0)
    u = _normalized(_cross(normal, reference))
    v = _cross(normal, u)
    corners = []
    for a, b in ((-1,-1), (1,-1), (1,1), (-1,1)):
        point = tuple(origin[i] + size * (a*u[i] + b*v[i]) for i in range(3))
        corners.append(gmsh.model.occ.addPoint(*point))
    lines = [gmsh.model.occ.addLine(corners[i], corners[(i+1) % 4]) for i in range(4)]
    loop = gmsh.model.occ.addCurveLoop(lines)
    return gmsh.model.occ.addPlaneSurface([loop])


def _cross(a, b):
    return (
        a[1]*b[2] - a[2]*b[1],
        a[2]*b[0] - a[0]*b[2],
        a[0]*b[1] - a[1]*b[0],
    )
