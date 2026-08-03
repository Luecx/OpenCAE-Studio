from __future__ import annotations

import math
from itertools import product

from opencae.model.selection import local_geometry_tags

from .errors import GeometryError


def apply_plane_partition(gmsh, part, feature) -> None:
    reference = getattr(feature, "datum_plane_ref", None)
    referenced_id = getattr(reference, "entity_id", "") if reference is not None else ""
    datum = _datum_plane(part, feature)
    if referenced_id and datum is None:
        raise GeometryError("The partition datum plane no longer exists")

    origin_values = datum.origin if datum is not None else feature.origin
    normal_values = datum.normal if datum is not None else feature.normal
    origin = tuple(float(value) for value in origin_values)
    normal = _normalized(tuple(float(value) for value in normal_values))

    target_tags = sorted(local_geometry_tags(part, feature.target, 3))
    objects = [(3, tag) for tag in target_tags] or list(gmsh.model.getEntities(3))
    if not objects:
        raise GeometryError("Plane partition requires at least one solid cell")

    # A datum plane is mathematically infinite.  Build only the finite OCC tool
    # needed to cover the target cells instead of centring an oversized square
    # on the datum origin.  The origin may be far away in the plane itself.
    corners = _covering_plane_corners(gmsh, objects, origin, normal)
    plane = _add_plane(gmsh, corners)

    result, result_map = gmsh.model.occ.fragment(
        objects,
        [(2, plane)],
        removeObject=True,
        removeTool=True,
    )
    gmsh.model.occ.synchronize()

    # BooleanFragments also returns pieces of the finite cutting tool that lie
    # outside the solid.  Those pieces are standalone faces with no adjacent
    # result volume and used to appear as a huge rectangular surface.  Keep
    # only descendants of the plane that are actual boundaries of the
    # partitioned volumes.
    _remove_external_plane_fragments(gmsh, objects, result, result_map)


def _datum_plane(part, feature):
    reference = getattr(feature, "datum_plane_ref", None)
    entity_id = getattr(reference, "entity_id", "") if reference is not None else ""
    if not entity_id:
        return None
    return next(
        (
            item
            for item in getattr(part, "datums", ())
            if getattr(item, "id", None) == entity_id
            and hasattr(item, "normal")
            and hasattr(item, "origin")
        ),
        None,
    )


def _normalized(vector):
    length = math.sqrt(sum(value * value for value in vector))
    if length <= 1.0e-14:
        raise GeometryError("Partition plane normal must not be zero")
    return tuple(value / length for value in vector)


def _covering_plane_corners(gmsh, objects, origin, normal):
    reference = (0.0, 0.0, 1.0) if abs(normal[2]) < 0.9 else (0.0, 1.0, 0.0)
    u = _normalized(_cross(normal, reference))
    v = _normalized(_cross(normal, u))

    projected_u: list[float] = []
    projected_v: list[float] = []
    model_diagonal = 0.0

    for dim, tag in objects:
        xmin, ymin, zmin, xmax, ymax, zmax = gmsh.model.getBoundingBox(dim, tag)
        model_diagonal = max(
            model_diagonal,
            math.sqrt((xmax - xmin) ** 2 + (ymax - ymin) ** 2 + (zmax - zmin) ** 2),
        )
        for x, y, z in product((xmin, xmax), (ymin, ymax), (zmin, zmax)):
            relative = (x - origin[0], y - origin[1], z - origin[2])
            projected_u.append(_dot(relative, u))
            projected_v.append(_dot(relative, v))

    if not projected_u or not projected_v:
        raise GeometryError("Could not determine the partition target bounds")

    umin, umax = min(projected_u), max(projected_u)
    vmin, vmax = min(projected_v), max(projected_v)
    span = max(umax - umin, vmax - vmin, model_diagonal, 1.0e-9)
    padding = max(span * 0.05, 1.0e-9)
    umin -= padding
    umax += padding
    vmin -= padding
    vmax += padding

    return [
        _point_on_plane(origin, u, v, umin, vmin),
        _point_on_plane(origin, u, v, umax, vmin),
        _point_on_plane(origin, u, v, umax, vmax),
        _point_on_plane(origin, u, v, umin, vmax),
    ]


def _add_plane(gmsh, corners):
    points = [gmsh.model.occ.addPoint(*corner) for corner in corners]
    lines = [gmsh.model.occ.addLine(points[index], points[(index + 1) % 4]) for index in range(4)]
    loop = gmsh.model.occ.addCurveLoop(lines)
    return gmsh.model.occ.addPlaneSurface([loop])


def _remove_external_plane_fragments(gmsh, objects, result, result_map) -> None:
    result_volumes = [(int(dim), int(tag)) for dim, tag in result if int(dim) == 3]
    if not result_volumes:
        raise GeometryError("The partition plane did not produce any solid cells")

    boundary = gmsh.model.getBoundary(
        result_volumes,
        combined=False,
        oriented=False,
        recursive=False,
    )
    volume_surface_tags = {abs(int(tag)) for dim, tag in boundary if int(dim) == 2}

    # outDimTagsMap follows the input order: all object cells, then the tool.
    tool_index = len(objects)
    if result_map and len(result_map) > tool_index:
        tool_descendants = result_map[tool_index]
    else:
        # Compatibility fallback for wrappers that omit the map.  With only
        # 3D objects and one 2D tool, explicit 2D Boolean outputs are tool
        # descendants; ordinary volume boundary faces are not listed here.
        tool_descendants = [(dim, tag) for dim, tag in result if int(dim) == 2]

    orphan_surfaces = sorted(
        {
            (2, abs(int(tag)))
            for dim, tag in tool_descendants
            if int(dim) == 2 and abs(int(tag)) not in volume_surface_tags
        }
    )
    if not orphan_surfaces:
        return

    gmsh.model.occ.remove(orphan_surfaces, recursive=True)
    gmsh.model.occ.synchronize()


def _point_on_plane(origin, u, v, u_value, v_value):
    return tuple(
        origin[index] + u_value * u[index] + v_value * v[index]
        for index in range(3)
    )


def _dot(a, b):
    return sum(a[index] * b[index] for index in range(3))


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )
