from __future__ import annotations

import numpy as np

from .datum_math import coordinate_point, edge_parameter, plane_axis, polyline_point, polyline_tangent, ref_curve, ref_direction, ref_point, unit, xyz
from .entities.datums import DatumPlane, DatumPoint, DatumVector


def create_datum(kind, name, method, parameters, entity_id=None):
    common = {"name": name, "method": method, "parameters": parameters}
    if entity_id is not None:
        common["id"] = entity_id
    if kind == "Point":
        return DatumPoint(position=tuple(_point(method, parameters)), **common)
    if kind == "Vector":
        origin, direction = _vector(method, parameters)
        return DatumVector(origin=tuple(origin), direction=tuple(direction), **common)
    origin, normal, axis = _plane(method, parameters)
    return DatumPlane(origin=tuple(origin), normal=tuple(normal), axis=tuple(axis), **common)


def _point(method, p):
    if method == "Coordinates": return coordinate_point(p)
    if method == "Existing Point": return ref_point(p.get("source"))
    if method == "Between Two Points":
        a, b, ratio = ref_point(p.get("point_1")), ref_point(p.get("point_2")), float(p.get("ratio", 0.5))
        return (1.0 - ratio) * a + ratio * b
    points = ref_curve(p.get("edge")); return polyline_point(points, edge_parameter(points,p))


def _vector(method, p):
    if method == "Components": return xyz(p, "origin"), unit(xyz(p, "direction"))
    if method == "Between Two Points":
        a, b = ref_point(p.get("point_1")), ref_point(p.get("point_2")); return a, unit(b - a)
    if method == "Along Edge":
        points = ref_curve(p.get("edge")); position = float(p.get("position", 0.5))
        return polyline_point(points, position), polyline_tangent(points, position) * (-1 if p.get("flip") else 1)
    if method == "Face Normal":
        ref = p.get("face") or {}; return ref_point(ref), unit(ref.get("normal", (0, 0, 1))) * (-1 if p.get("flip") else 1)
    return xyz(p, "origin"), unit(p.get("axis", (1, 0, 0)))


def _plane(method, p):
    if method == "Point and Normal":
        origin = ref_point(p.get("point")); normal = unit(ref_direction(p.get("normal"))); return origin, normal, plane_axis(normal)
    if method == "Three Points":
        a, b, c = (ref_point(p.get(key)) for key in ("point_1", "point_2", "point_3"))
        normal = unit(np.cross(b - a, c - a)); return a, normal, unit(b - a)
    if method == "Offset from Face / Plane":
        ref = p.get("reference") or {}; normal = unit(ref.get("normal", (0, 0, 1)))
        origin = ref_point(ref) + float(p.get("offset", 0.0)) * normal; return origin, normal, plane_axis(normal)
    if method == "Principal CSYS Plane":
        origin, normal, axis = xyz(p, "origin"), unit(p.get("normal", (0, 0, 1))), unit(p.get("axis", (1, 0, 0)))
        return origin + float(p.get("offset", 0.0)) * normal, normal, axis
    edge, point = ref_curve(p.get("edge")), ref_point(p.get("point")); origin = edge[0]
    tangent = unit(edge[-1] - edge[0]); normal = unit(np.cross(tangent, point - origin)); return origin, normal, tangent


