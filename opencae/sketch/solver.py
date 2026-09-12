"""Numerical 2D geometric-constraint solver used by the OpenCAE sketcher."""

from __future__ import annotations

from dataclasses import dataclass
from math import acos, atan2, cos, hypot, pi, sin
from typing import Iterable

import numpy as np
from scipy.optimize import least_squares

from opencae.model.entities.geometry import (
    SketchArc,
    SketchCircle,
    SketchConstraint,
    SketchDefinition,
    SketchEllipse,
    SketchLine,
    SketchSpline,
)

_EPS = 1.0e-10


@dataclass(frozen=True)
class SketchSolveResult:
    success: bool
    message: str
    residual_norm: float
    degrees_of_freedom: int
    rank: int
    variables: int
    residuals: int

    @property
    def fully_constrained(self) -> bool:
        return self.success and self.degrees_of_freedom <= 0


class SketchConstraintError(ValueError):
    pass


class _Variables:
    """Flatten sketch degrees of freedom while retaining semantic lookup."""

    def __init__(self, sketch: SketchDefinition):
        self.sketch = sketch
        self.points = sketch.point_map()
        self.entities = sketch.entity_map()
        self.point_slots: dict[str, tuple[int, int]] = {}
        self.scalar_slots: dict[tuple[str, str], int] = {}
        values: list[float] = []
        for point in sketch.points:
            self.point_slots[point.id] = (len(values), len(values) + 1)
            values.extend((float(point.x), float(point.y)))
        for entity in sketch.entities:
            if isinstance(entity, SketchCircle):
                self.scalar_slots[(entity.id, "radius")] = len(values)
                values.append(float(entity.radius))
            elif isinstance(entity, SketchEllipse):
                self.scalar_slots[(entity.id, "minor_radius")] = len(values)
                values.append(float(entity.minor_radius))
        self.x0 = np.asarray(values, dtype=float)

    @property
    def size(self) -> int:
        return int(self.x0.size)

    def point(self, point_id: str, x: np.ndarray) -> np.ndarray:
        try:
            ix, iy = self.point_slots[str(point_id)]
        except KeyError as exc:
            raise SketchConstraintError(f"Unknown sketch point '{point_id}'") from exc
        return np.asarray((x[ix], x[iy]), dtype=float)

    def scalar(self, entity_id: str, name: str, x: np.ndarray) -> float:
        try:
            return float(x[self.scalar_slots[(str(entity_id), str(name))]])
        except KeyError as exc:
            raise SketchConstraintError(
                f"Unknown sketch scalar '{entity_id}:{name}'"
            ) from exc

    def entity(self, ref: str):
        entity_id, _ = _parse_entity_ref(ref)
        try:
            return self.entities[entity_id]
        except KeyError as exc:
            raise SketchConstraintError(f"Unknown sketch entity '{entity_id}'") from exc

    def point_ref(self, ref: str, x: np.ndarray) -> np.ndarray:
        raw = str(ref or "")
        if raw.startswith("point:"):
            return self.point(raw.split(":", 1)[1], x)
        if raw in self.point_slots:
            return self.point(raw, x)
        entity_id, location = _parse_entity_ref(raw)
        entity = self.entities.get(entity_id)
        if entity is None:
            raise SketchConstraintError(f"Unknown point reference '{raw}'")
        point_id = _entity_point_id(entity, location)
        if point_id is None:
            raise SketchConstraintError(f"'{raw}' does not identify a sketch point")
        return self.point(point_id, x)

    def line_points(self, ref: str, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        entity = self.entity(ref)
        if not isinstance(entity, SketchLine):
            raise SketchConstraintError("Constraint requires a line")
        return self.point(entity.start, x), self.point(entity.end, x)

    def center(self, ref: str, x: np.ndarray) -> np.ndarray:
        entity = self.entity(ref)
        if isinstance(entity, (SketchCircle, SketchArc, SketchEllipse)):
            return self.point(entity.center, x)
        raise SketchConstraintError("Constraint requires a centered entity")

    def radius(self, ref: str, x: np.ndarray) -> float:
        entity = self.entity(ref)
        if isinstance(entity, SketchCircle):
            return abs(self.scalar(entity.id, "radius", x))
        if isinstance(entity, SketchArc):
            center = self.point(entity.center, x)
            start = self.point(entity.start, x)
            return _length(start - center)
        if isinstance(entity, SketchEllipse):
            center = self.point(entity.center, x)
            major = self.point(entity.major, x)
            return _length(major - center)
        raise SketchConstraintError("Constraint requires a circular entity")

    def entity_points(self, ref: str) -> tuple[str, ...]:
        entity = self.entity(ref)
        if isinstance(entity, SketchLine):
            return entity.start, entity.end
        if isinstance(entity, SketchCircle):
            return (entity.center,)
        if isinstance(entity, SketchArc):
            return entity.center, entity.start, entity.end
        if isinstance(entity, SketchEllipse):
            return entity.center, entity.major
        if isinstance(entity, SketchSpline):
            return tuple(entity.points)
        return ()

    def apply(self, x: np.ndarray) -> None:
        for point in self.sketch.points:
            ix, iy = self.point_slots[point.id]
            point.x = float(x[ix])
            point.y = float(x[iy])
        for entity in self.sketch.entities:
            if isinstance(entity, SketchCircle):
                entity.radius = max(
                    abs(float(x[self.scalar_slots[(entity.id, "radius")]])),
                    1.0e-9,
                )
            elif isinstance(entity, SketchEllipse):
                entity.minor_radius = max(
                    abs(float(x[self.scalar_slots[(entity.id, "minor_radius")]])),
                    1.0e-9,
                )


def solve_sketch(
    sketch: SketchDefinition,
    *,
    tolerance: float = 1.0e-7,
    max_nfev: int = 250,
) -> SketchSolveResult:
    """Solve the sketch in place and return rank/DOF diagnostics.

    The sketch model deliberately stores human-readable constraints rather than
    solver equations. This function translates those constraints into scaled
    residual equations and uses SciPy's trust-region least-squares solver. The
    same path is used during interactive edits and before OCC feature creation,
    so persisted dimensions are always authoritative.
    """

    variables = _Variables(sketch)
    if variables.size == 0:
        return SketchSolveResult(True, "Empty sketch", 0.0, 0, 0, 0, 0)

    fixed_targets = {
        point.id: np.asarray((point.x, point.y), dtype=float)
        for point in sketch.points
        if point.fixed
    }
    constraint_fixed_targets = _capture_fixed_constraint_targets(
        variables, sketch.constraints, variables.x0
    )

    def residual(x: np.ndarray) -> np.ndarray:
        values: list[float] = []
        _intrinsic_residuals(variables, x, values)
        for point_id, target in fixed_targets.items():
            current = variables.point(point_id, x)
            values.extend((current - target).tolist())
        for constraint in sketch.constraints:
            if not constraint.driving and _normal_kind(constraint.kind) in _DIMENSION_KINDS:
                continue
            _constraint_residuals(
                variables,
                constraint,
                x,
                values,
                constraint_fixed_targets,
            )
        return np.asarray(values or [0.0], dtype=float)

    try:
        initial = residual(variables.x0)
        if np.linalg.norm(initial) <= tolerance:
            x = variables.x0.copy()
            jac = _finite_difference_jacobian(residual, x)
            success = True
            message = "Solved"
        else:
            result = least_squares(
                residual,
                variables.x0,
                method="trf",
                xtol=1.0e-11,
                ftol=1.0e-11,
                gtol=1.0e-11,
                max_nfev=int(max_nfev),
                x_scale="jac",
            )
            x = np.asarray(result.x, dtype=float)
            jac = np.asarray(result.jac, dtype=float)
            success = bool(result.success)
            message = str(result.message)
        values = residual(x)
        norm = float(np.linalg.norm(values))
        if not np.isfinite(norm) or norm > max(float(tolerance), 1.0e-6) * max(1.0, np.sqrt(values.size)):
            success = False
            message = "Sketch constraints are inconsistent or could not converge"
        if success:
            variables.apply(x)
        rank = int(np.linalg.matrix_rank(jac, tol=1.0e-8)) if jac.size else 0
        dof = max(0, variables.size - rank)
        return SketchSolveResult(
            success,
            message,
            norm,
            dof,
            rank,
            variables.size,
            int(values.size),
        )
    except (SketchConstraintError, ValueError, FloatingPointError) as exc:
        return SketchSolveResult(
            False,
            str(exc),
            float("inf"),
            variables.size,
            0,
            variables.size,
            0,
        )


def constraint_label(constraint: SketchConstraint) -> str:
    kind = str(constraint.kind or "Constraint")
    if constraint.value is None:
        return constraint.name or kind
    value = float(constraint.value)
    suffix = "°" if _normal_kind(kind) == "angle" else ""
    return constraint.name or f"{kind}: {value:g}{suffix}"


def entity_length(sketch: SketchDefinition, entity_id: str) -> float | None:
    variables = _Variables(sketch)
    x = variables.x0
    entity = variables.entities.get(str(entity_id))
    if isinstance(entity, SketchLine):
        a = variables.point(entity.start, x)
        b = variables.point(entity.end, x)
        return _length(b - a)
    if isinstance(entity, SketchCircle):
        return 2.0 * pi * variables.radius(entity.id, x)
    if isinstance(entity, SketchArc):
        c = variables.point(entity.center, x)
        a = variables.point(entity.start, x) - c
        b = variables.point(entity.end, x) - c
        angle = _directed_angle(a, b, entity.clockwise)
        return variables.radius(entity.id, x) * abs(angle)
    return None


_DIMENSION_KINDS = {
    "distance",
    "distancex",
    "distancey",
    "horizontal distance",
    "vertical distance",
    "angle",
    "radius",
    "diameter",
    "length",
}


def _constraint_residuals(
    variables: _Variables,
    constraint: SketchConstraint,
    x: np.ndarray,
    out: list[float],
    fixed_targets: dict[str, tuple[tuple[int, float], ...]],
) -> None:
    kind = _normal_kind(constraint.kind)
    refs = tuple(str(ref) for ref in constraint.refs)
    value = None if constraint.value is None else float(constraint.value)

    if kind == "coincident":
        _require_refs(kind, refs, 2)
        out.extend((variables.point_ref(refs[0], x) - variables.point_ref(refs[1], x)).tolist())
        return
    if kind in {"horizontal", "vertical"}:
        a, b = _two_points_or_line(variables, refs, x)
        out.append(float((b - a)[1 if kind == "horizontal" else 0]))
        return
    if kind in {"parallel", "perpendicular", "angle"}:
        _require_refs(kind, refs, 2)
        d1 = _unit(_line_vector(variables, refs[0], x))
        d2 = _unit(_line_vector(variables, refs[1], x))
        if kind == "parallel":
            out.append(_cross2(d1, d2))
        elif kind == "perpendicular":
            out.append(float(np.dot(d1, d2)))
        else:
            if value is None:
                raise SketchConstraintError("Angle constraint requires a value")
            target = np.deg2rad(value)
            current = atan2(_cross2(d1, d2), float(np.dot(d1, d2)))
            out.append(_wrap_angle(current - target))
        return
    if kind == "collinear":
        _require_refs(kind, refs, 2)
        a1, b1 = variables.line_points(refs[0], x)
        a2, b2 = variables.line_points(refs[1], x)
        direction = _unit(b1 - a1)
        out.extend((_cross2(direction, a2 - a1), _cross2(direction, b2 - a1)))
        return
    if kind in {"equal", "equal length"}:
        _require_refs(kind, refs, 2)
        first = variables.entity(refs[0])
        second = variables.entity(refs[1])
        if isinstance(first, SketchLine) and isinstance(second, SketchLine):
            out.append(_line_length(variables, refs[0], x) - _line_length(variables, refs[1], x))
        elif isinstance(first, (SketchCircle, SketchArc)) and isinstance(second, (SketchCircle, SketchArc)):
            out.append(variables.radius(refs[0], x) - variables.radius(refs[1], x))
        else:
            raise SketchConstraintError("Equal requires two lines or two circular entities")
        return
    if kind == "concentric":
        _require_refs(kind, refs, 2)
        out.extend((variables.center(refs[0], x) - variables.center(refs[1], x)).tolist())
        return
    if kind == "midpoint":
        _require_refs(kind, refs, 2)
        point = variables.point_ref(refs[0], x)
        a, b = variables.line_points(refs[1], x)
        out.extend((point - 0.5 * (a + b)).tolist())
        return
    if kind in {"point on object", "pointonobject"}:
        _require_refs(kind, refs, 2)
        point = variables.point_ref(refs[0], x)
        entity = variables.entity(refs[1])
        if isinstance(entity, SketchLine):
            a, b = variables.line_points(refs[1], x)
            direction = _unit(b - a)
            out.append(_cross2(direction, point - a))
        elif isinstance(entity, (SketchCircle, SketchArc)):
            out.append(_length(point - variables.center(refs[1], x)) - variables.radius(refs[1], x))
        else:
            raise SketchConstraintError("Point-on-object supports lines, circles and arcs")
        return
    if kind == "symmetry":
        _require_refs(kind, refs, 3)
        p1 = variables.point_ref(refs[0], x)
        p2 = variables.point_ref(refs[1], x)
        a, b = variables.line_points(refs[2], x)
        axis = _unit(b - a)
        midpoint = 0.5 * (p1 + p2)
        segment = p2 - p1
        out.append(_cross2(axis, midpoint - a))
        out.append(float(np.dot(axis, segment)))
        return
    if kind in {"distance", "length"}:
        if value is None:
            raise SketchConstraintError("Distance constraint requires a value")
        if len(refs) == 1:
            out.append(_line_length(variables, refs[0], x) - value)
        else:
            _require_refs(kind, refs, 2)
            out.append(_length(variables.point_ref(refs[1], x) - variables.point_ref(refs[0], x)) - value)
        return
    if kind in {"distancex", "horizontal distance"}:
        _require_refs(kind, refs, 2)
        if value is None:
            raise SketchConstraintError("Horizontal distance requires a value")
        out.append(float(variables.point_ref(refs[1], x)[0] - variables.point_ref(refs[0], x)[0] - value))
        return
    if kind in {"distancey", "vertical distance"}:
        _require_refs(kind, refs, 2)
        if value is None:
            raise SketchConstraintError("Vertical distance requires a value")
        out.append(float(variables.point_ref(refs[1], x)[1] - variables.point_ref(refs[0], x)[1] - value))
        return
    if kind in {"radius", "diameter"}:
        _require_refs(kind, refs, 1)
        if value is None:
            raise SketchConstraintError(f"{constraint.kind} constraint requires a value")
        target = value * (0.5 if kind == "diameter" else 1.0)
        out.append(variables.radius(refs[0], x) - target)
        return
    if kind == "tangent":
        _require_refs(kind, refs, 2)
        _tangent_residual(variables, refs[0], refs[1], x, out)
        return
    if kind == "fixed":
        target = fixed_targets.get(constraint.id, ())
        if not target:
            raise SketchConstraintError("Fixed constraint has no resolvable geometry")
        for index, expected in target:
            out.append(float(x[index] - expected))
        return
    if kind in {"construction", "reference"}:
        return
    raise SketchConstraintError(f"Unsupported sketch constraint: {constraint.kind}")


def _intrinsic_residuals(variables: _Variables, x: np.ndarray, out: list[float]) -> None:
    for entity in variables.sketch.entities:
        if isinstance(entity, SketchArc):
            center = variables.point(entity.center, x)
            start = variables.point(entity.start, x)
            end = variables.point(entity.end, x)
            out.append(_length(start - center) - _length(end - center))
        elif isinstance(entity, SketchCircle):
            radius = variables.scalar(entity.id, "radius", x)
            if radius < 1.0e-9:
                out.append(radius - 1.0e-9)
        elif isinstance(entity, SketchEllipse):
            center = variables.point(entity.center, x)
            major = variables.point(entity.major, x)
            major_radius = _length(major - center)
            minor = variables.scalar(entity.id, "minor_radius", x)
            if major_radius < 1.0e-9:
                out.append(major_radius - 1.0e-9)
            if minor < 1.0e-9:
                out.append(minor - 1.0e-9)


def _capture_fixed_constraint_targets(
    variables: _Variables,
    constraints: Iterable[SketchConstraint],
    x: np.ndarray,
) -> dict[str, tuple[tuple[int, float], ...]]:
    result: dict[str, tuple[tuple[int, float], ...]] = {}
    for constraint in constraints:
        if _normal_kind(constraint.kind) != "fixed":
            continue
        indexes: list[int] = []
        for ref in constraint.refs:
            raw = str(ref)
            if raw.startswith("point:") or raw in variables.point_slots:
                point_id = raw.split(":", 1)[1] if raw.startswith("point:") else raw
                indexes.extend(variables.point_slots.get(point_id, ()))
                continue
            try:
                entity_id, _ = _parse_entity_ref(raw)
                entity = variables.entities[entity_id]
            except (KeyError, SketchConstraintError):
                continue
            for point_id in variables.entity_points(entity_id):
                indexes.extend(variables.point_slots.get(point_id, ()))
            if isinstance(entity, SketchCircle):
                indexes.append(variables.scalar_slots[(entity.id, "radius")])
            elif isinstance(entity, SketchEllipse):
                indexes.append(variables.scalar_slots[(entity.id, "minor_radius")])
        unique = tuple(dict.fromkeys(indexes))
        result[constraint.id] = tuple((index, float(x[index])) for index in unique)
    return result


def _tangent_residual(
    variables: _Variables,
    first_ref: str,
    second_ref: str,
    x: np.ndarray,
    out: list[float],
) -> None:
    first = variables.entity(first_ref)
    second = variables.entity(second_ref)
    if isinstance(first, SketchLine) and isinstance(second, (SketchCircle, SketchArc)):
        line_ref, curve_ref = first_ref, second_ref
    elif isinstance(second, SketchLine) and isinstance(first, (SketchCircle, SketchArc)):
        line_ref, curve_ref = second_ref, first_ref
    elif isinstance(first, (SketchCircle, SketchArc)) and isinstance(second, (SketchCircle, SketchArc)):
        c1 = variables.center(first_ref, x)
        c2 = variables.center(second_ref, x)
        distance = _length(c2 - c1)
        r1 = variables.radius(first_ref, x)
        r2 = variables.radius(second_ref, x)
        # Let the nearest valid internal/external tangency branch win.
        external = distance - (r1 + r2)
        internal = distance - abs(r1 - r2)
        out.append(external if abs(external) <= abs(internal) else internal)
        return
    else:
        raise SketchConstraintError("Tangent supports line/circle/arc combinations")
    a, b = variables.line_points(line_ref, x)
    center = variables.center(curve_ref, x)
    direction = _unit(b - a)
    distance = abs(_cross2(direction, center - a))
    out.append(distance - variables.radius(curve_ref, x))


def _two_points_or_line(
    variables: _Variables,
    refs: tuple[str, ...],
    x: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    if len(refs) == 1:
        return variables.line_points(refs[0], x)
    _require_refs("constraint", refs, 2)
    return variables.point_ref(refs[0], x), variables.point_ref(refs[1], x)


def _line_vector(variables: _Variables, ref: str, x: np.ndarray) -> np.ndarray:
    a, b = variables.line_points(ref, x)
    return b - a


def _line_length(variables: _Variables, ref: str, x: np.ndarray) -> float:
    return _length(_line_vector(variables, ref, x))


def _entity_point_id(entity, location: str | None) -> str | None:
    location = (location or "").casefold()
    if isinstance(entity, SketchLine):
        if location in {"", "start", "p1", "0"}:
            return entity.start
        if location in {"end", "p2", "1"}:
            return entity.end
    elif isinstance(entity, (SketchCircle, SketchArc, SketchEllipse)):
        if location in {"", "center", "c"}:
            return entity.center
        if isinstance(entity, SketchArc):
            if location in {"start", "p1", "0"}:
                return entity.start
            if location in {"end", "p2", "1"}:
                return entity.end
        if isinstance(entity, SketchEllipse) and location in {"major", "axis", "p1"}:
            return entity.major
    elif isinstance(entity, SketchSpline):
        if not entity.points:
            return None
        if location in {"", "start", "p1", "0"}:
            return entity.points[0]
        if location in {"end", "p2"}:
            return entity.points[-1]
        if location.startswith("p") and location[1:].isdigit():
            index = int(location[1:])
            if 0 <= index < len(entity.points):
                return entity.points[index]
    return None


def _parse_entity_ref(ref: str) -> tuple[str, str | None]:
    raw = str(ref or "")
    if raw.startswith("entity:"):
        raw = raw[len("entity:"):]
    parts = raw.split(":", 1)
    if not parts[0]:
        raise SketchConstraintError("Empty entity reference")
    return parts[0], parts[1] if len(parts) == 2 else None


def _normal_kind(value: str) -> str:
    return " ".join(str(value or "").strip().casefold().replace("_", " ").split())


def _require_refs(kind: str, refs: tuple[str, ...], count: int) -> None:
    if len(refs) < count:
        raise SketchConstraintError(f"{kind.title()} requires {count} references")


def _length(vector: np.ndarray) -> float:
    return float(hypot(float(vector[0]), float(vector[1])))


def _unit(vector: np.ndarray) -> np.ndarray:
    length = _length(vector)
    if length <= _EPS:
        raise SketchConstraintError("Zero-length geometry cannot be constrained")
    return np.asarray(vector, dtype=float) / length


def _cross2(a: np.ndarray, b: np.ndarray) -> float:
    return float(a[0] * b[1] - a[1] * b[0])


def _directed_angle(a: np.ndarray, b: np.ndarray, clockwise: bool) -> float:
    value = atan2(_cross2(a, b), float(np.dot(a, b)))
    if clockwise and value > 0.0:
        value -= 2.0 * pi
    elif not clockwise and value < 0.0:
        value += 2.0 * pi
    return value


def _wrap_angle(value: float) -> float:
    return (float(value) + pi) % (2.0 * pi) - pi


def _finite_difference_jacobian(function, x: np.ndarray) -> np.ndarray:
    base = function(x)
    jac = np.empty((base.size, x.size), dtype=float)
    step = 1.0e-7
    for index in range(x.size):
        shifted = x.copy()
        shifted[index] += step * max(1.0, abs(float(x[index])))
        actual_step = shifted[index] - x[index]
        jac[:, index] = (function(shifted) - base) / actual_step
    return jac
