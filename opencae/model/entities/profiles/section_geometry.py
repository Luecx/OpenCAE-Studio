"""Discretize profile definitions into local quadrilateral section patches.

The returned patches describe non-overlapping material area in local ``(y, z)``
coordinates about the profile centroid. Standard profiles are deliberately
quadrangulated so physical beam visualization can extrude every patch into one
VTK hexahedron without introducing triangular caps or overlapping solids.

Straight wall/arm segments use four patches (five stations) along their length.
Classical thin-walled profiles keep flange/web or wall/wall intersections as
explicit corner/junction rectangles instead of hiding those regions inside one
of the adjacent strips.
"""

from __future__ import annotations

import math

import numpy as np

from .base import Profile

_LINEAR_SEGMENTS = 4
_EPS = 1.0e-12


def section_patches(profile: Profile, circle_segments: int = 24) -> tuple[np.ndarray, ...]:
    """Return quadrilateral material patches for one profile."""
    kind = str(getattr(profile, "profile_type", "General"))
    values = dict(getattr(profile, "dimensions", {}) or {})
    properties = dict(profile.properties() or {})
    cy = float(properties.get("Centroid y", 0.0) or 0.0)
    cz = float(properties.get("Centroid z", 0.0) or 0.0)

    if kind == "Rectangle":
        patches = _subdivide_rect(
            _rectangle(_positive(values, "width"), _positive(values, "height"))
        )
    elif kind == "Box":
        patches = _box(values)
    elif kind == "Circle":
        patches = _circle_quads(_positive(values, "diameter") * 0.5, circle_segments)
    elif kind == "Pipe":
        patches = _pipe(values, circle_segments)
    elif kind in {"I-profile", "H-profile"}:
        patches = _i_profile(values)
    elif kind in {"C-profile", "Channel"}:
        patches = _channel(values)
    elif kind == "U-profile":
        patches = _u_profile(values)
    elif kind == "Graph profile":
        patches = _graph(values)
    else:
        patches = _subdivide_rect(_equivalent_rectangle(properties))

    offset = np.asarray((cy, cz), dtype=float)
    result = []
    for patch in patches:
        polygon = np.asarray(patch, dtype=float)
        if polygon.shape != (4, 2):
            continue
        if not np.all(np.isfinite(polygon)):
            continue
        polygon = polygon - offset
        if abs(_signed_area(polygon)) <= 1.0e-14:
            continue
        result.append(polygon)
    return tuple(result)


def _rectangle(width: float, height: float) -> np.ndarray:
    width = max(float(width), 1.0e-9)
    height = max(float(height), 1.0e-9)
    return np.asarray(
        (
            (-width / 2, -height / 2),
            (width / 2, -height / 2),
            (width / 2, height / 2),
            (-width / 2, height / 2),
        ),
        dtype=float,
    )


def _box(values) -> tuple[np.ndarray, ...]:
    """Partition a hollow box into explicit corners plus subdivided wall strips."""
    width = _positive(values, "width")
    height = _positive(values, "height")
    thickness = min(_positive(values, "thickness"), width / 2, height / 2)
    if thickness <= 0.0:
        return _subdivide_rect(_rectangle(width, height))

    y0, y1 = -width / 2, width / 2
    z0, z1 = -height / 2, height / 2
    iy0, iy1 = y0 + thickness, y1 - thickness
    iz0, iz1 = z0 + thickness, z1 - thickness
    if iy1 <= iy0 + _EPS or iz1 <= iz0 + _EPS:
        return _subdivide_rect(_rectangle(width, height))

    corners = (
        _rect_bounds(y0, iy0, z0, iz0),
        _rect_bounds(iy1, y1, z0, iz0),
        _rect_bounds(iy1, y1, iz1, z1),
        _rect_bounds(y0, iy0, iz1, z1),
    )
    strips = (
        _rect_bounds(iy0, iy1, z0, iz0),
        _rect_bounds(iy0, iy1, iz1, z1),
        _rect_bounds(y0, iy0, iz0, iz1),
        _rect_bounds(iy1, y1, iz0, iz1),
    )
    patches = list(corners)
    for strip in strips:
        patches.extend(_subdivide_rect(strip))
    return tuple(patches)


def _circle_quads(radius: float, segments: int) -> tuple[np.ndarray, ...]:
    """Map a structured square grid onto a disk to obtain only quad patches."""
    radius = max(float(radius), 1.0e-9)
    perimeter_segments = max(8, int(segments))
    divisions = max(2, int(round(perimeter_segments / 4)))
    coordinates = np.linspace(-1.0, 1.0, divisions + 1)
    patches = []
    for i in range(divisions):
        u0, u1 = coordinates[i], coordinates[i + 1]
        for j in range(divisions):
            v0, v1 = coordinates[j], coordinates[j + 1]
            patches.append(
                np.asarray(
                    (
                        _square_to_disk(u0, v0, radius),
                        _square_to_disk(u1, v0, radius),
                        _square_to_disk(u1, v1, radius),
                        _square_to_disk(u0, v1, radius),
                    ),
                    dtype=float,
                )
            )
    return tuple(patches)


def _square_to_disk(u: float, v: float, radius: float) -> tuple[float, float]:
    # Fernández-Guasti squircle mapping. The square boundary maps exactly onto
    # the circle while preserving a structured quadrilateral interior.
    y = radius * u * math.sqrt(max(0.0, 1.0 - 0.5 * v * v))
    z = radius * v * math.sqrt(max(0.0, 1.0 - 0.5 * u * u))
    return y, z


def _pipe(values, segments: int) -> tuple[np.ndarray, ...]:
    outer = _positive(values, "diameter") * 0.5
    thickness = min(_positive(values, "thickness"), outer)
    inner = max(outer - thickness, 0.0)
    if inner <= 1.0e-12:
        return _circle_quads(outer, segments)
    count = max(8, int(segments))
    angles = np.linspace(0.0, 2.0 * math.pi, count + 1)
    patches = []
    for first, second in zip(angles[:-1], angles[1:], strict=True):
        patches.append(
            np.asarray(
                (
                    (outer * math.cos(first), outer * math.sin(first)),
                    (outer * math.cos(second), outer * math.sin(second)),
                    (inner * math.cos(second), inner * math.sin(second)),
                    (inner * math.cos(first), inner * math.sin(first)),
                ),
                dtype=float,
            )
        )
    return tuple(patches)


def _i_profile(values) -> tuple[np.ndarray, ...]:
    """Partition I/H material into junction blocks and subdivided clear strips."""
    height, width, web, flange = _open_dimensions(values)
    y0, y1 = -width / 2, width / 2
    wy0, wy1 = -web / 2, web / 2
    z0, z1 = -height / 2, height / 2
    fz0, fz1 = z0 + flange, z1 - flange

    patches = [
        _rect_bounds(wy0, wy1, z0, fz0),
        _rect_bounds(wy0, wy1, fz1, z1),
    ]
    for strip in (
        _rect_bounds(y0, wy0, z0, fz0),
        _rect_bounds(wy1, y1, z0, fz0),
        _rect_bounds(y0, wy0, fz1, z1),
        _rect_bounds(wy1, y1, fz1, z1),
        _rect_bounds(wy0, wy1, fz0, fz1),
    ):
        patches.extend(_subdivide_rect(strip))
    return tuple(patches)


def _channel(values) -> tuple[np.ndarray, ...]:
    """Partition channel material into corner blocks and subdivided clear strips."""
    height, width, web, flange = _open_dimensions(values)
    patches = [
        _rect_bounds(0.0, web, 0.0, flange),
        _rect_bounds(0.0, web, height - flange, height),
    ]
    for strip in (
        _rect_bounds(web, width, 0.0, flange),
        _rect_bounds(web, width, height - flange, height),
        _rect_bounds(0.0, web, flange, height - flange),
    ):
        patches.extend(_subdivide_rect(strip))
    return tuple(patches)


def _u_profile(values) -> tuple[np.ndarray, ...]:
    """Partition U material into corner blocks and subdivided base/leg strips."""
    overall_width = _positive(values, "height")
    leg_height = _positive(values, "flange_width")
    base = min(_positive(values, "web_thickness"), leg_height)
    leg = min(_positive(values, "flange_thickness"), overall_width / 2)
    patches = [
        _rect_bounds(0.0, leg, 0.0, base),
        _rect_bounds(overall_width - leg, overall_width, 0.0, base),
    ]
    for strip in (
        _rect_bounds(leg, overall_width - leg, 0.0, base),
        _rect_bounds(0.0, leg, base, leg_height),
        _rect_bounds(overall_width - leg, overall_width, base, leg_height),
    ):
        patches.extend(_subdivide_rect(strip))
    return tuple(patches)


def _graph(values) -> tuple[np.ndarray, ...]:
    nodes = _graph_nodes(values.get("nodes", values.get("points", "")))
    default = float(values.get("thickness", 2.0) or 2.0)
    segments = str(values.get("segments", "") or "")
    if not segments and len(nodes) > 1:
        ids = list(nodes)
        segments = "\n".join(f"{a},{b},{default}" for a, b in zip(ids, ids[1:]))
    patches = []
    for line in segments.replace(";", "\n").splitlines():
        try:
            first_id, second_id, raw_thickness = (
                item.strip() for item in line.split(",", 2)
            )
            first = np.asarray(nodes[int(first_id)], dtype=float)
            second = np.asarray(nodes[int(second_id)], dtype=float)
            thickness = max(float(raw_thickness), 0.0)
        except (KeyError, TypeError, ValueError):
            continue
        tangent = second - first
        length = float(np.linalg.norm(tangent))
        if length <= 1.0e-12 or thickness <= 0.0:
            continue
        normal = np.asarray((-tangent[1], tangent[0])) / length * thickness * 0.5
        for index in range(_LINEAR_SEGMENTS):
            a = index / _LINEAR_SEGMENTS
            b = (index + 1) / _LINEAR_SEGMENTS
            start = first + a * tangent
            end = first + b * tangent
            patches.append(
                np.asarray(
                    (
                        start + normal,
                        end + normal,
                        end - normal,
                        start - normal,
                    )
                )
            )
    return tuple(patches)


def _graph_nodes(text) -> dict[int, tuple[float, float]]:
    result = {}
    for line in str(text or "").replace(";", "\n").splitlines():
        try:
            tag, y, z = (item.strip() for item in line.split(",", 2))
            result[int(tag)] = (float(y), float(z))
        except (TypeError, ValueError):
            continue
    return result


def _equivalent_rectangle(properties) -> np.ndarray:
    area = max(float(properties.get("Area", 0.0) or 0.0), 1.0e-9)
    iyy = max(float(properties.get("Iyy", 0.0) or 0.0), 0.0)
    izz = max(float(properties.get("Izz", 0.0) or 0.0), 0.0)
    if iyy > 0.0 and izz > 0.0:
        height = math.sqrt(12.0 * iyy / area)
        width = math.sqrt(12.0 * izz / area)
        product = max(width * height, 1.0e-18)
        scale = math.sqrt(area / product)
        width *= scale
        height *= scale
    else:
        width = height = math.sqrt(area)
    return _rectangle(width, height)


def _open_dimensions(values) -> tuple[float, float, float, float]:
    height = _positive(values, "height")
    width = _positive(values, "flange_width")
    web = min(_positive(values, "web_thickness"), width)
    flange = min(_positive(values, "flange_thickness"), height / 2)
    return height, width, web, flange


def _subdivide_rect(patch: np.ndarray, segments: int = _LINEAR_SEGMENTS) -> tuple[np.ndarray, ...]:
    """Split a rectangular strip along its longer local axis into equal patches."""
    polygon = np.asarray(patch, dtype=float)
    if polygon.shape != (4, 2):
        return ()
    edge_01 = float(np.linalg.norm(polygon[1] - polygon[0]))
    edge_12 = float(np.linalg.norm(polygon[2] - polygon[1]))
    if edge_01 <= _EPS or edge_12 <= _EPS:
        return ()
    count = max(1, int(segments))
    if count == 1:
        return (polygon,)

    result = []
    for index in range(count):
        a = index / count
        b = (index + 1) / count
        if edge_01 >= edge_12:
            p0 = (1.0 - a) * polygon[0] + a * polygon[1]
            p1 = (1.0 - b) * polygon[0] + b * polygon[1]
            p2 = (1.0 - b) * polygon[3] + b * polygon[2]
            p3 = (1.0 - a) * polygon[3] + a * polygon[2]
        else:
            p0 = (1.0 - a) * polygon[0] + a * polygon[3]
            p1 = (1.0 - a) * polygon[1] + a * polygon[2]
            p2 = (1.0 - b) * polygon[1] + b * polygon[2]
            p3 = (1.0 - b) * polygon[0] + b * polygon[3]
        result.append(np.asarray((p0, p1, p2, p3), dtype=float))
    return tuple(result)


def _rect_bounds(y0, y1, z0, z1) -> np.ndarray:
    return np.asarray(
        ((y0, z0), (y1, z0), (y1, z1), (y0, z1)),
        dtype=float,
    )


def _signed_area(polygon: np.ndarray) -> float:
    y = polygon[:, 0]
    z = polygon[:, 1]
    return 0.5 * float(np.sum(y * np.roll(z, -1) - z * np.roll(y, -1)))


def _positive(values, key) -> float:
    return max(float(values.get(key, 0.0) or 0.0), 0.0)
