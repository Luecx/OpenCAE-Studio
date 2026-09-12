"""Persistent parametric 2D sketch entities and sketch-based geometry features."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot
from uuid import uuid4

from ...core import register_model_type
from .feature import GeometryFeature


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


@register_model_type("sketch_point")
@dataclass
class SketchPoint:
    """One editable 2D degree-of-freedom point in sketch coordinates."""

    id: str = field(default_factory=lambda: _uid("sp"))
    x: float = 0.0
    y: float = 0.0
    construction: bool = False
    fixed: bool = False

    def xy(self) -> tuple[float, float]:
        return float(self.x), float(self.y)


@register_model_type("sketch_line")
@dataclass
class SketchLine:
    id: str = field(default_factory=lambda: _uid("sl"))
    start: str = ""
    end: str = ""
    construction: bool = False


@register_model_type("sketch_circle")
@dataclass
class SketchCircle:
    id: str = field(default_factory=lambda: _uid("sc"))
    center: str = ""
    radius: float = 1.0
    construction: bool = False


@register_model_type("sketch_arc")
@dataclass
class SketchArc:
    """Circular arc defined by center/start/end sketch points."""

    id: str = field(default_factory=lambda: _uid("sa"))
    center: str = ""
    start: str = ""
    end: str = ""
    clockwise: bool = False
    construction: bool = False


@register_model_type("sketch_ellipse")
@dataclass
class SketchEllipse:
    """Full ellipse with an oriented major axis and scalar minor radius."""

    id: str = field(default_factory=lambda: _uid("se"))
    center: str = ""
    major: str = ""
    minor_radius: float = 1.0
    construction: bool = False


@register_model_type("sketch_spline")
@dataclass
class SketchSpline:
    """Interpolating B-spline through ordered sketch control points."""

    id: str = field(default_factory=lambda: _uid("ss"))
    points: tuple[str, ...] = ()
    closed: bool = False
    construction: bool = False


@register_model_type("sketch_constraint")
@dataclass
class SketchConstraint:
    """One geometric or dimensional constraint.

    ``refs`` use compact handles such as ``point:<id>`` or ``entity:<id>``.
    Point handles can also use semantic entity locations like
    ``entity:<id>:start`` and ``entity:<id>:center``; the solver resolves them
    through the entity topology rather than persisting UI objects.
    """

    id: str = field(default_factory=lambda: _uid("skc"))
    kind: str = "Coincident"
    refs: tuple[str, ...] = ()
    value: float | None = None
    driving: bool = True
    name: str = ""


@register_model_type("sketch_definition")
@dataclass
class SketchDefinition:
    """Editable sketch graph in its local XY plane."""

    points: list[SketchPoint] = field(default_factory=list)
    entities: list[object] = field(default_factory=list)
    constraints: list[SketchConstraint] = field(default_factory=list)
    grid_spacing: float = 10.0
    snap_grid: bool = True
    snap_geometry: bool = True

    def point_map(self) -> dict[str, SketchPoint]:
        return {point.id: point for point in self.points}

    def entity_map(self) -> dict[str, object]:
        return {getattr(entity, "id", ""): entity for entity in self.entities}

    def point(self, point_id: str) -> SketchPoint:
        try:
            return self.point_map()[str(point_id)]
        except KeyError as exc:
            raise KeyError(f"Unknown sketch point: {point_id}") from exc

    def add_point(
        self,
        x: float,
        y: float,
        *,
        construction: bool = False,
        fixed: bool = False,
    ) -> SketchPoint:
        point = SketchPoint(
            x=float(x), y=float(y), construction=construction, fixed=fixed
        )
        self.points.append(point)
        return point

    def add_line(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        *,
        construction: bool = False,
    ) -> SketchLine:
        p1 = self.add_point(*start, construction=construction)
        p2 = self.add_point(*end, construction=construction)
        entity = SketchLine(
            start=p1.id, end=p2.id, construction=construction
        )
        self.entities.append(entity)
        return entity

    def add_circle(
        self,
        center: tuple[float, float],
        radius: float,
        *,
        construction: bool = False,
    ) -> SketchCircle:
        point = self.add_point(*center, construction=construction)
        entity = SketchCircle(
            center=point.id,
            radius=max(abs(float(radius)), 1.0e-9),
            construction=construction,
        )
        self.entities.append(entity)
        return entity

    def add_arc(
        self,
        center: tuple[float, float],
        start: tuple[float, float],
        end: tuple[float, float],
        *,
        clockwise: bool = False,
        construction: bool = False,
    ) -> SketchArc:
        pc = self.add_point(*center, construction=construction)
        ps = self.add_point(*start, construction=construction)
        pe = self.add_point(*end, construction=construction)
        entity = SketchArc(
            center=pc.id,
            start=ps.id,
            end=pe.id,
            clockwise=bool(clockwise),
            construction=construction,
        )
        self.entities.append(entity)
        return entity

    def add_ellipse(
        self,
        center: tuple[float, float],
        major: tuple[float, float],
        minor_radius: float,
        *,
        construction: bool = False,
    ) -> SketchEllipse:
        pc = self.add_point(*center, construction=construction)
        pm = self.add_point(*major, construction=construction)
        entity = SketchEllipse(
            center=pc.id,
            major=pm.id,
            minor_radius=max(abs(float(minor_radius)), 1.0e-9),
            construction=construction,
        )
        self.entities.append(entity)
        return entity

    def add_spline(
        self,
        coordinates: list[tuple[float, float]],
        *,
        closed: bool = False,
        construction: bool = False,
    ) -> SketchSpline:
        ids = tuple(
            self.add_point(*xy, construction=construction).id
            for xy in coordinates
        )
        entity = SketchSpline(
            points=ids,
            closed=bool(closed),
            construction=construction,
        )
        self.entities.append(entity)
        return entity

    def bounds(self) -> tuple[float, float, float, float] | None:
        if not self.points:
            return None
        xs = [float(point.x) for point in self.points]
        ys = [float(point.y) for point in self.points]
        # Include scalar radii that may extend beyond explicit point positions.
        for entity in self.entities:
            if isinstance(entity, SketchCircle):
                center = self.point(entity.center)
                r = abs(float(entity.radius))
                xs.extend((center.x - r, center.x + r))
                ys.extend((center.y - r, center.y + r))
            elif isinstance(entity, SketchEllipse):
                center = self.point(entity.center)
                major = self.point(entity.major)
                a = hypot(major.x - center.x, major.y - center.y)
                b = abs(float(entity.minor_radius))
                extent = max(a, b)
                xs.extend((center.x - extent, center.x + extent))
                ys.extend((center.y - extent, center.y + extent))
        return min(xs), min(ys), max(xs), max(ys)


@register_model_type("sketch_feature")
@dataclass
class SketchFeature(GeometryFeature):
    """Parametric profile plus the operation that creates Part geometry."""

    feature_type: str = field(init=False, default="Sketch Feature")
    mode: str = "Extrusion"  # Extrusion, Revolve, Planar
    operation: str = "New"  # New, Add, Cut, Intersect
    sketch: SketchDefinition = field(default_factory=SketchDefinition)
    depth: float = 10.0
    angle_degrees: float = 360.0
    symmetric: bool = False
    reverse: bool = False
    revolve_axis: str = "X"

    def __post_init__(self):
        super().__post_init__()
        self.mode = str(self.mode or "Extrusion")
        self.operation = str(self.operation or "New")
        self.depth = max(abs(float(self.depth)), 1.0e-9)
        self.angle_degrees = max(min(abs(float(self.angle_degrees)), 360.0), 1.0e-6)
        self.revolve_axis = str(self.revolve_axis or "X").upper()


SKETCH_ENTITY_TYPES = (
    SketchLine,
    SketchCircle,
    SketchArc,
    SketchEllipse,
    SketchSpline,
)

__all__ = [
    "SketchPoint",
    "SketchLine",
    "SketchCircle",
    "SketchArc",
    "SketchEllipse",
    "SketchSpline",
    "SketchConstraint",
    "SketchDefinition",
    "SketchFeature",
    "SKETCH_ENTITY_TYPES",
]
