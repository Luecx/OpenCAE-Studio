from __future__ import annotations

import numpy as np

from opencae.model.entities.datums import DatumPlane, DatumPoint, DatumVector
from opencae.model.selection import SelectableKind, ViewportHit

from .instance_transform import transform_points, transform_vector


def reference_from_hit(viewport, hit: ViewportHit) -> dict:
    """Convert one typed viewport hit into the geometric data datum builders use.

    Datum definitions intentionally store the resolved geometry needed to preview
    and rebuild themselves (point coordinates, edge polyline, surface normal,
    and so on).  Region picking only needs identity, so the normal viewport hit
    is deliberately smaller.  This adapter is the boundary between those two
    representations.
    """
    if not isinstance(hit, ViewportHit):
        raise TypeError("Datum reference picking requires a ViewportHit")

    common = {
        "name": hit.label or _fallback_name(hit),
        "entity_id": hit.entity_id,
        "instance_id": hit.instance_id,
        "tag": hit.topology_tag,
    }
    kind = hit.kind

    if kind == SelectableKind.GEOMETRY_VERTEX:
        point = _required_point(hit.world_position, "The selected vertex has no position")
        return {**common, "kind": "vertex", "point": point, "origin": point}

    if kind == SelectableKind.GEOMETRY_EDGE:
        points = _geometry_points(viewport, hit, dimension=1)
        if len(points) < 2:
            raise ValueError("The selected edge has no usable curve points")
        return {
            **common,
            "kind": "edge",
            "point": tuple(np.mean(points, axis=0)),
            "origin": tuple(points[0]),
            "points": tuple(tuple(value) for value in points),
            "direction": _unit_tuple(points[-1] - points[0]),
        }

    if kind == SelectableKind.GEOMETRY_FACE:
        points, faces = _surface_geometry(viewport, hit)
        if len(points) < 3:
            raise ValueError("The selected face has no usable surface points")
        normal = _surface_normal(points, faces)
        point = tuple(np.mean(points, axis=0))
        return {
            **common,
            "kind": "face",
            "point": point,
            "origin": point,
            "points": tuple(tuple(value) for value in points),
            "normal": normal,
            "direction": normal,
        }

    entity = _entity(viewport, hit)
    instance = viewport.scene.instance_for(hit.instance_id) if hit.instance_id else None

    if kind == SelectableKind.REFERENCE_POINT:
        point = _required_point(hit.world_position, "The selected reference point has no position")
        return {**common, "kind": "reference_point", "point": point, "origin": point}

    if kind == SelectableKind.DATUM_POINT:
        point = hit.world_position
        if point is None and isinstance(entity, DatumPoint):
            point = _transform_point(entity.position, instance)
        point = _required_point(point, "The selected datum point has no position")
        return {**common, "kind": "datum_point", "point": point, "origin": point}

    if kind == SelectableKind.DATUM_VECTOR:
        if not isinstance(entity, DatumVector):
            raise ValueError("The selected datum vector no longer exists")
        origin = _transform_point(entity.origin, instance)
        direction = _transform_direction(entity.direction, instance)
        return {
            **common,
            "kind": "datum_vector",
            "point": origin,
            "origin": origin,
            "direction": direction,
        }

    if kind == SelectableKind.DATUM_PLANE:
        if not isinstance(entity, DatumPlane):
            raise ValueError("The selected datum plane no longer exists")
        origin = _transform_point(entity.origin, instance)
        normal = _transform_direction(entity.normal, instance)
        axis = _transform_direction(entity.axis, instance)
        return {
            **common,
            "kind": "datum_plane",
            "point": origin,
            "origin": origin,
            "normal": normal,
            "direction": normal,
            "axis": axis,
        }

    raise ValueError(f"{kind.value.replace('_', ' ').title()} cannot define a datum reference")


def _entity(viewport, hit):
    store = getattr(viewport, "store", None)
    project = getattr(store, "project", None)
    if project is None or not hit.entity_id:
        return None
    return project.try_resolve(hit.entity_id)


def _geometry_points(viewport, hit, dimension):
    snapshot = viewport.scene.snapshot_for(hit.instance_id)
    if snapshot is None or hit.topology_tag is None:
        return np.empty((0, 3), dtype=float)
    collection = snapshot.vertices if dimension == 0 else snapshot.edges if dimension == 1 else snapshot.surfaces
    patch = next((item for item in collection if int(item.tag) == int(hit.topology_tag)), None)
    if patch is None:
        return np.empty((0, 3), dtype=float)
    values = np.asarray([patch.point] if dimension == 0 else patch.points, dtype=float)
    instance = viewport.scene.instance_for(hit.instance_id) if hit.instance_id else None
    return transform_points(values, instance) if instance is not None else values


def _surface_geometry(viewport, hit):
    snapshot = viewport.scene.snapshot_for(hit.instance_id)
    if snapshot is None or hit.topology_tag is None:
        return np.empty((0, 3), dtype=float), np.empty(0, dtype=np.int64)
    patch = next((item for item in snapshot.surfaces if int(item.tag) == int(hit.topology_tag)), None)
    if patch is None:
        return np.empty((0, 3), dtype=float), np.empty(0, dtype=np.int64)
    points = np.asarray(patch.points, dtype=float)
    instance = viewport.scene.instance_for(hit.instance_id) if hit.instance_id else None
    if instance is not None:
        points = transform_points(points, instance)
    return points, np.asarray(patch.faces, dtype=np.int64).ravel()


def _surface_normal(points, faces):
    cursor = 0
    while cursor < len(faces):
        count = int(faces[cursor])
        indices = faces[cursor + 1:cursor + 1 + count]
        cursor += count + 1
        if count < 3:
            continue
        base = points[int(indices[0])]
        for index in range(1, count - 1):
            first = points[int(indices[index])] - base
            second = points[int(indices[index + 1])] - base
            cross = np.cross(first, second)
            norm = float(np.linalg.norm(cross))
            if norm > 1.0e-14:
                return tuple(cross / norm)

    centered = points - np.mean(points, axis=0)
    if len(centered) >= 3:
        _u, _s, vh = np.linalg.svd(centered, full_matrices=False)
        if len(vh) >= 3:
            return _unit_tuple(vh[-1])
    raise ValueError("The selected face normal could not be determined")


def _required_point(value, message):
    if value is None:
        raise ValueError(message)
    point = tuple(float(component) for component in value)
    if len(point) != 3:
        raise ValueError(message)
    return point


def _transform_point(value, instance):
    point = np.asarray(value, dtype=float)
    if instance is not None:
        point = transform_points([point], instance)[0]
    return tuple(float(component) for component in point)


def _transform_direction(value, instance):
    vector = np.asarray(value, dtype=float)
    if instance is not None:
        vector = transform_vector(vector, instance)
    return _unit_tuple(vector)


def _unit_tuple(value):
    vector = np.asarray(value, dtype=float)
    norm = float(np.linalg.norm(vector))
    if norm <= 1.0e-14:
        raise ValueError("The selected reference has a zero direction")
    return tuple(float(component) for component in vector / norm)


def _fallback_name(hit):
    if hit.topology_tag is not None:
        label = {
            SelectableKind.GEOMETRY_VERTEX: "Vertex",
            SelectableKind.GEOMETRY_EDGE: "Edge",
            SelectableKind.GEOMETRY_FACE: "Face",
        }.get(hit.kind, hit.kind.value.replace("_", " ").title())
        return f"{label}-{hit.topology_tag}"
    return hit.kind.value.replace("_", " ").title()
