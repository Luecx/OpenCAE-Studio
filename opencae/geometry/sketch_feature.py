"""Build parametric SketchFeature profiles with Gmsh's OpenCASCADE kernel."""

from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, hypot, pi, sin

import numpy as np

from opencae.model.entities.geometry import (
    SketchArc,
    SketchCircle,
    SketchEllipse,
    SketchFeature,
    SketchLine,
    SketchSpline,
)
from opencae.sketch import solve_sketch

from .errors import GeometryError


_EPS = 1.0e-9


@dataclass
class _CurveRecord:
    """One OCC curve plus the 2D topology used to assemble profile loops."""

    tag: int
    start: tuple[float, float] | None
    end: tuple[float, float] | None
    samples: list[tuple[float, float]]
    closed: bool = False


@dataclass
class _LoopRecord:
    """A closed OCC wire and its sampled 2D polygon for nesting tests."""

    wire_tag: int
    curve_tags: list[int]
    samples: list[tuple[float, float]]
    area: float
    parent: int | None = None
    depth: int = 0


def apply_sketch_feature(gmsh, feature: SketchFeature) -> None:
    """Solve and apply one sketch-based planar, extrusion or revolve feature."""
    result = solve_sketch(feature.sketch)
    if not result.success:
        raise GeometryError(f"Sketch is not solvable: {result.message}")

    existing_volumes = list(gmsh.model.getEntities(3))
    existing_surfaces = list(gmsh.model.getEntities(2))
    surfaces, loops = _create_profile_surfaces(gmsh, feature)
    if not surfaces:
        raise GeometryError(
            "Sketch does not contain a closed non-construction profile"
        )

    mode = str(feature.mode or "Extrusion").strip().casefold()
    if mode == "planar":
        created = [(2, tag) for tag in surfaces]
        _apply_operation(gmsh, feature, existing_surfaces, created, 2)
        gmsh.model.occ.synchronize()
        return

    if mode == "extrusion":
        _extrude(gmsh, feature, surfaces, existing_volumes)
        return

    if mode == "revolve":
        _revolve(gmsh, feature, surfaces, loops, existing_volumes)
        return

    raise GeometryError(f"Unsupported sketch feature mode: {feature.mode}")


def _extrude(gmsh, feature: SketchFeature, surfaces: list[int], existing) -> None:
    distance = max(abs(float(feature.depth)), _EPS)
    signed = -distance if feature.reverse else distance
    dimtags = [(2, tag) for tag in surfaces]
    if feature.symmetric:
        gmsh.model.occ.translate(dimtags, 0.0, 0.0, -0.5 * signed)

    output = gmsh.model.occ.extrude(dimtags, 0.0, 0.0, signed)
    created = [(dim, tag) for dim, tag in output if dim == 3]
    if not created:
        raise GeometryError("Extrusion did not create a solid")

    _apply_operation(gmsh, feature, existing, created, 3)
    gmsh.model.occ.synchronize()


def _revolve(
    gmsh,
    feature: SketchFeature,
    surfaces: list[int],
    loops: list[_LoopRecord],
    existing,
) -> None:
    if str(feature.revolve_axis or "X").upper() != "X":
        raise GeometryError(
            "Only the sketch X axis is currently supported for revolve"
        )

    _validate_revolve_profile(loops)
    angle = np.deg2rad(
        max(min(abs(float(feature.angle_degrees)), 360.0), 1.0e-6)
    )
    if feature.reverse:
        angle = -angle

    dimtags = [(2, tag) for tag in surfaces]
    if feature.symmetric:
        gmsh.model.occ.rotate(
            dimtags,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            -0.5 * float(angle),
        )

    output = gmsh.model.occ.revolve(
        dimtags,
        0.0,
        0.0,
        0.0,
        1.0,
        0.0,
        0.0,
        float(angle),
    )
    created = [(dim, tag) for dim, tag in output if dim == 3]
    if not created:
        raise GeometryError("Revolve did not create a solid")

    _apply_operation(gmsh, feature, existing, created, 3)
    gmsh.model.occ.synchronize()


def _apply_operation(gmsh, feature, existing, created, dimension: int) -> None:
    """Apply the feature's boolean policy to already-existing geometry."""
    operation = str(feature.operation or "New").strip().casefold()
    if operation == "new" or not existing:
        return

    if operation == "add":
        result, _ = gmsh.model.occ.fuse(
            list(existing),
            list(created),
            removeObject=True,
            removeTool=True,
        )
    elif operation == "cut":
        result, _ = gmsh.model.occ.cut(
            list(existing),
            list(created),
            removeObject=True,
            removeTool=True,
        )
    elif operation == "intersect":
        result, _ = gmsh.model.occ.intersect(
            list(existing),
            list(created),
            removeObject=True,
            removeTool=True,
        )
    else:
        raise GeometryError(
            f"Unsupported sketch boolean operation: {feature.operation}"
        )

    if not any(dim == dimension for dim, _ in result):
        raise GeometryError(
            f"Sketch {feature.operation} operation produced no geometry"
        )


def _create_profile_surfaces(gmsh, feature: SketchFeature):
    sketch = feature.sketch
    points = sketch.point_map()
    point_tags: dict[str, int] = {}

    def point_tag(point_id: str) -> int:
        try:
            point = points[point_id]
        except KeyError as exc:
            raise GeometryError(
                f"Sketch references missing point {point_id}"
            ) from exc
        if point_id not in point_tags:
            point_tags[point_id] = gmsh.model.occ.addPoint(
                float(point.x),
                float(point.y),
                0.0,
            )
        return point_tags[point_id]

    curves: list[_CurveRecord] = []
    for entity in sketch.entities:
        if bool(getattr(entity, "construction", False)):
            continue
        try:
            record = _create_occ_curve(
                gmsh,
                entity,
                points,
                point_tag,
            )
            if record is not None:
                curves.append(record)
        except GeometryError:
            raise
        except Exception as exc:
            raise GeometryError(
                f"Could not create sketch curve: {exc}"
            ) from exc

    if not curves:
        return [], []

    loops = _assemble_loops(gmsh, curves, sketch.grid_spacing)
    _classify_loop_nesting(loops)

    surfaces: list[int] = []
    for index, loop in enumerate(loops):
        if loop.depth % 2:
            continue
        holes = [
            child.wire_tag
            for child in loops
            if child.parent == index and child.depth == loop.depth + 1
        ]
        surfaces.append(
            gmsh.model.occ.addPlaneSurface([loop.wire_tag, *holes])
        )

    gmsh.model.occ.synchronize()
    return surfaces, loops


def _create_occ_curve(gmsh, entity, points, point_tag):
    if isinstance(entity, SketchLine):
        a = points[entity.start].xy()
        b = points[entity.end].xy()
        if _distance(a, b) <= _EPS:
            raise GeometryError("Sketch contains a zero-length line")
        tag = gmsh.model.occ.addLine(
            point_tag(entity.start),
            point_tag(entity.end),
        )
        return _CurveRecord(tag, a, b, [a, b])

    if isinstance(entity, SketchCircle):
        center = points[entity.center].xy()
        radius = max(abs(float(entity.radius)), _EPS)
        tag = gmsh.model.occ.addCircle(
            center[0],
            center[1],
            0.0,
            radius,
        )
        samples = [
            (
                center[0] + radius * cos(2.0 * pi * i / 64.0),
                center[1] + radius * sin(2.0 * pi * i / 64.0),
            )
            for i in range(64)
        ]
        samples.append(samples[0])
        return _CurveRecord(tag, None, None, samples, True)

    if isinstance(entity, SketchArc):
        center = points[entity.center].xy()
        start = points[entity.start].xy()
        end = points[entity.end].xy()
        r0 = _distance(center, start)
        r1 = _distance(center, end)
        if min(r0, r1) <= _EPS:
            raise GeometryError("Sketch arc has zero radius")
        if abs(r0 - r1) > max(r0, r1, 1.0) * 1.0e-6:
            raise GeometryError(
                "Sketch arc endpoints are not on the same circle"
            )

        # OpenCASCADE resolves wire orientation from connectivity. The curve
        # itself is therefore always stored under its positive OCC tag.
        if entity.clockwise:
            tag = gmsh.model.occ.addCircleArc(
                point_tag(entity.end),
                point_tag(entity.center),
                point_tag(entity.start),
            )
        else:
            tag = gmsh.model.occ.addCircleArc(
                point_tag(entity.start),
                point_tag(entity.center),
                point_tag(entity.end),
            )
        samples = _arc_samples(center, start, end, bool(entity.clockwise))
        return _CurveRecord(tag, start, end, samples)

    if isinstance(entity, SketchEllipse):
        center = points[entity.center].xy()
        major = points[entity.major].xy()
        dx = major[0] - center[0]
        dy = major[1] - center[1]
        major_radius = hypot(dx, dy)
        minor_radius = max(abs(float(entity.minor_radius)), _EPS)
        if major_radius <= _EPS:
            raise GeometryError("Sketch ellipse has zero major radius")
        if minor_radius > major_radius + 1.0e-9:
            raise GeometryError(
                "Sketch ellipse minor radius cannot exceed its major radius"
            )
        angle = atan2(dy, dx)
        tag = gmsh.model.occ.addEllipse(
            center[0],
            center[1],
            0.0,
            major_radius,
            minor_radius,
            -1,
            0.0,
            2.0 * pi,
            [0.0, 0.0, 1.0],
            [cos(angle), sin(angle), 0.0],
        )
        samples = _ellipse_samples(
            center,
            major_radius,
            minor_radius,
            angle,
        )
        return _CurveRecord(tag, None, None, samples, True)

    if isinstance(entity, SketchSpline):
        if len(entity.points) < 2:
            raise GeometryError("Sketch spline requires at least two points")
        tags = [point_tag(point_id) for point_id in entity.points]
        coordinates = [points[point_id].xy() for point_id in entity.points]
        if entity.closed:
            tags.append(tags[0])
            coordinates.append(coordinates[0])
        tag = gmsh.model.occ.addSpline(tags)
        return _CurveRecord(
            tag,
            None if entity.closed else coordinates[0],
            None if entity.closed else coordinates[-1],
            _sample_polyline(coordinates),
            bool(entity.closed),
        )

    return None


def _assemble_loops(
    gmsh,
    curves: list[_CurveRecord],
    grid_spacing: float,
) -> list[_LoopRecord]:
    """Assemble profile loops according to OpenCASCADE wire semantics.

    ``occ.addCurveLoop`` does not accept ``reorient`` and ignores negative curve
    tags. Curves are therefore ordered by endpoint connectivity and their
    positive OCC tags are passed to OpenCASCADE, which resolves edge orientation
    when constructing the closed wire.
    """
    tolerance = max(abs(float(grid_spacing)) * 1.0e-6, 1.0e-7)
    loops: list[_LoopRecord] = []
    open_curves: dict[int, _CurveRecord] = {}

    for index, curve in enumerate(curves):
        if curve.closed:
            wire = gmsh.model.occ.addCurveLoop([int(curve.tag)])
            samples = _ensure_closed(curve.samples)
            loops.append(
                _LoopRecord(
                    wire,
                    [int(curve.tag)],
                    samples,
                    _signed_area(samples),
                )
            )
        else:
            open_curves[index] = curve

    if not open_curves:
        return loops

    node_for: dict[tuple[int, int], list[tuple[int, bool]]] = {}
    for index, curve in open_curves.items():
        assert curve.start is not None and curve.end is not None
        node_for.setdefault(
            _node_key(curve.start, tolerance), []
        ).append((index, True))
        node_for.setdefault(
            _node_key(curve.end, tolerance), []
        ).append((index, False))

    unused = set(open_curves)
    while unused:
        first_index = next(iter(unused))
        first = open_curves[first_index]
        assert first.start is not None and first.end is not None

        start_key = _node_key(first.start, tolerance)
        current_key = _node_key(first.end, tolerance)
        tags = [int(first.tag)]
        samples = list(first.samples)
        unused.remove(first_index)

        while current_key != start_key:
            candidates = [
                pair
                for pair in node_for.get(current_key, ())
                if pair[0] in unused
            ]
            if not candidates:
                raise GeometryError(
                    "Sketch profile is open. Join all non-construction "
                    "endpoints before finishing."
                )
            if len(candidates) > 1:
                raise GeometryError(
                    "Sketch profile branches at an endpoint. A solid profile "
                    "must form unambiguous closed loops."
                )

            next_index, enters_at_start = candidates[0]
            curve = open_curves[next_index]
            assert curve.start is not None and curve.end is not None
            tags.append(int(curve.tag))

            if enters_at_start:
                samples.extend(curve.samples[1:])
                current_key = _node_key(curve.end, tolerance)
            else:
                samples.extend(list(reversed(curve.samples[:-1])))
                current_key = _node_key(curve.start, tolerance)

            unused.remove(next_index)

        samples = _ensure_closed(samples)
        wire = gmsh.model.occ.addCurveLoop(tags)
        loops.append(
            _LoopRecord(
                wire,
                tags,
                samples,
                _signed_area(samples),
            )
        )

    return loops


def _classify_loop_nesting(loops: list[_LoopRecord]) -> None:
    """Assign each loop to its smallest containing parent loop."""
    for index, loop in enumerate(loops):
        if len(loop.samples) < 4:
            continue
        probe = _interior_probe(loop.samples)
        containers: list[tuple[float, int]] = []
        for other_index, other in enumerate(loops):
            if index == other_index:
                continue
            if abs(other.area) <= abs(loop.area) + _EPS:
                continue
            if _point_in_polygon(probe, other.samples):
                containers.append((abs(other.area), other_index))
        if containers:
            _, loop.parent = min(containers)

    for index, loop in enumerate(loops):
        depth = 0
        parent = loop.parent
        seen = {index}
        while parent is not None and parent not in seen:
            seen.add(parent)
            depth += 1
            parent = loops[parent].parent
        loop.depth = depth


def _validate_revolve_profile(loops: list[_LoopRecord]) -> None:
    """Reject profiles that cross the fixed sketch X revolve axis."""
    values = [point[1] for loop in loops for point in loop.samples]
    positive = any(value > 1.0e-7 for value in values)
    negative = any(value < -1.0e-7 for value in values)
    if positive and negative:
        raise GeometryError(
            "A revolved profile may touch the X axis but cannot cross it. "
            "Keep the closed profile entirely on one side of the revolve axis."
        )


def _arc_samples(
    center,
    start,
    end,
    clockwise: bool,
    count: int = 32,
):
    radius = _distance(center, start)
    a0 = atan2(start[1] - center[1], start[0] - center[0])
    a1 = atan2(end[1] - center[1], end[0] - center[0])
    if clockwise:
        while a1 >= a0:
            a1 -= 2.0 * pi
    else:
        while a1 <= a0:
            a1 += 2.0 * pi

    return [
        (
            center[0] + radius * cos(a0 + (a1 - a0) * i / count),
            center[1] + radius * sin(a0 + (a1 - a0) * i / count),
        )
        for i in range(count + 1)
    ]


def _ellipse_samples(
    center,
    a: float,
    b: float,
    angle: float,
    count: int = 64,
):
    ca = cos(angle)
    sa = sin(angle)
    result: list[tuple[float, float]] = []
    for index in range(count):
        t = 2.0 * pi * index / count
        x = a * cos(t)
        y = b * sin(t)
        result.append(
            (
                center[0] + ca * x - sa * y,
                center[1] + sa * x + ca * y,
            )
        )
    result.append(result[0])
    return result


def _sample_polyline(points, subdivisions: int = 6):
    if len(points) <= 1:
        return list(points)

    result = [points[0]]
    for first, second in zip(points, points[1:]):
        for index in range(1, subdivisions + 1):
            t = index / subdivisions
            result.append(
                (
                    first[0] + (second[0] - first[0]) * t,
                    first[1] + (second[1] - first[1]) * t,
                )
            )
    return result


def _node_key(point, tolerance: float):
    return (
        int(round(float(point[0]) / tolerance)),
        int(round(float(point[1]) / tolerance)),
    )


def _distance(a, b):
    return hypot(
        float(a[0]) - float(b[0]),
        float(a[1]) - float(b[1]),
    )


def _ensure_closed(points):
    values = list(points)
    if values and _distance(values[0], values[-1]) > _EPS:
        values.append(values[0])
    return values


def _signed_area(points):
    values = _ensure_closed(points)
    return 0.5 * sum(
        first[0] * second[1] - second[0] * first[1]
        for first, second in zip(values, values[1:])
    )


def _interior_probe(points):
    values = (
        points[:-1]
        if len(points) > 1 and points[0] == points[-1]
        else points
    )
    if not values:
        return 0.0, 0.0

    mean = (
        sum(point[0] for point in values) / len(values),
        sum(point[1] for point in values) / len(values),
    )
    if _point_in_polygon(mean, points):
        return mean

    if len(values) < 2:
        return mean

    a, b = values[0], values[1]
    mid = (
        (a[0] + b[0]) * 0.5,
        (a[1] + b[1]) * 0.5,
    )
    area = _signed_area(points)
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    length = max(hypot(dx, dy), _EPS)
    sign = 1.0 if area > 0.0 else -1.0
    offset = max(length * 1.0e-7, 1.0e-8)
    return (
        mid[0] - sign * dy / length * offset,
        mid[1] + sign * dx / length * offset,
    )


def _point_in_polygon(point, polygon):
    x, y = point
    values = _ensure_closed(polygon)
    inside = False
    for a, b in zip(values, values[1:]):
        if (a[1] > y) == (b[1] > y):
            continue
        denominator = b[1] - a[1]
        if abs(denominator) <= _EPS:
            continue
        x_cross = (
            (b[0] - a[0]) * (y - a[1]) / denominator + a[0]
        )
        if x < x_cross:
            inside = not inside
    return inside
