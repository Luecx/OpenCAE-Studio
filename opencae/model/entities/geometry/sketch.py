"""Persistent parametric 2D sketch entities and sketch-based geometry features."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from math import hypot
from uuid import uuid4

from ...core import register_model_type
from .feature import GeometryFeature


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class _CoercibleStrEnum(StrEnum):
    """Finite persistent domain with tolerant text input at API/UI boundaries."""

    @classmethod
    def coerce(cls, value):
        if isinstance(value, cls):
            return value
        text = str(value or "").strip()
        normalized = " ".join(text.casefold().replace("_", " ").split())
        for item in cls:
            if normalized in {
                " ".join(item.value.casefold().replace("_", " ").split()),
                item.name.casefold().replace("_", " "),
            }:
                return item
        aliases = getattr(cls, "_ALIASES", {})
        target = aliases.get(normalized)
        if target is not None:
            return target
        raise ValueError(f"Unknown {cls.__name__}: {value!r}")


class SketchConstraintKind(_CoercibleStrEnum):
    COINCIDENT = "Coincident"
    HORIZONTAL = "Horizontal"
    VERTICAL = "Vertical"
    PARALLEL = "Parallel"
    PERPENDICULAR = "Perpendicular"
    TANGENT = "Tangent"
    EQUAL = "Equal"
    CONCENTRIC = "Concentric"
    MIDPOINT = "Midpoint"
    COLLINEAR = "Collinear"
    POINT_ON_OBJECT = "Point on object"
    SYMMETRY = "Symmetry"
    FIXED = "Fixed"
    DISTANCE = "Distance"
    DISTANCE_X = "DistanceX"
    DISTANCE_Y = "DistanceY"
    ANGLE = "Angle"
    RADIUS = "Radius"
    DIAMETER = "Diameter"
    CONSTRUCTION = "Construction"
    REFERENCE = "Reference"


SketchConstraintKind._ALIASES = {
    "horizontal distance": SketchConstraintKind.DISTANCE_X,
    "vertical distance": SketchConstraintKind.DISTANCE_Y,
    "length": SketchConstraintKind.DISTANCE,
    "equal length": SketchConstraintKind.EQUAL,
    "pointonobject": SketchConstraintKind.POINT_ON_OBJECT,
}


class SketchFeatureMode(_CoercibleStrEnum):
    PLANAR = "Planar"
    EXTRUSION = "Extrusion"
    REVOLVE = "Revolve"


class SketchBooleanOperation(_CoercibleStrEnum):
    NEW = "New"
    ADD = "Add"
    CUT = "Cut"
    INTERSECT = "Intersect"


class SketchAxis(_CoercibleStrEnum):
    X = "X"


@dataclass(kw_only=True)
class SketchObject:
    """Identity-bearing object owned by one SketchDefinition.

    The marker is consumed by the model codec so shared topology is serialized
    once and restored with Python object identity intact. IDs are persistence/UI
    identity only; relationships are normal object references. Like project
    Entities, that identity is immutable after construction.
    """

    __model_identity__ = True

    id: str = field(default_factory=lambda: _uid("so"))

    def __setattr__(self, name, value) -> None:
        if name == "id" and "id" in self.__dict__ and self.__dict__["id"] != value:
            raise AttributeError("SketchObject.id is immutable")
        object.__setattr__(self, name, value)


@register_model_type("sketch_point")
@dataclass(kw_only=True)
class SketchPoint(SketchObject):
    """One editable 2D degree-of-freedom point in sketch coordinates."""

    id: str = field(default_factory=lambda: _uid("sp"))
    x: float = 0.0
    y: float = 0.0
    construction: bool = False
    fixed: bool = False

    def xy(self) -> tuple[float, float]:
        return float(self.x), float(self.y)


@register_model_type("sketch_line")
@dataclass(kw_only=True)
class SketchLine(SketchObject):
    id: str = field(default_factory=lambda: _uid("sl"))
    start: SketchPoint
    end: SketchPoint
    construction: bool = False

    def __post_init__(self):
        _require_points(self.start, self.end)


@register_model_type("sketch_circle")
@dataclass(kw_only=True)
class SketchCircle(SketchObject):
    id: str = field(default_factory=lambda: _uid("sc"))
    center: SketchPoint
    radius: float = 1.0
    construction: bool = False

    def __post_init__(self):
        _require_points(self.center)
        self.radius = max(abs(float(self.radius)), 1.0e-9)


@register_model_type("sketch_arc")
@dataclass(kw_only=True)
class SketchArc(SketchObject):
    """Circular arc defined by center/start/end sketch points."""

    id: str = field(default_factory=lambda: _uid("sa"))
    center: SketchPoint
    start: SketchPoint
    end: SketchPoint
    clockwise: bool = False
    construction: bool = False

    def __post_init__(self):
        _require_points(self.center, self.start, self.end)


@register_model_type("sketch_ellipse")
@dataclass(kw_only=True)
class SketchEllipse(SketchObject):
    """Full ellipse with an oriented major axis and scalar minor radius."""

    id: str = field(default_factory=lambda: _uid("se"))
    center: SketchPoint
    major: SketchPoint
    minor_radius: float = 1.0
    construction: bool = False

    def __post_init__(self):
        _require_points(self.center, self.major)
        self.minor_radius = max(abs(float(self.minor_radius)), 1.0e-9)


@register_model_type("sketch_spline")
@dataclass(kw_only=True)
class SketchSpline(SketchObject):
    """Interpolating B-spline through ordered sketch control points."""

    id: str = field(default_factory=lambda: _uid("ss"))
    points: tuple[SketchPoint, ...] = ()
    closed: bool = False
    construction: bool = False

    def __post_init__(self):
        self.points = tuple(self.points)
        _require_points(*self.points)
        if len(self.points) < 2:
            raise ValueError("SketchSpline requires at least two SketchPoint objects")


SKETCH_ENTITY_TYPES = (
    SketchLine,
    SketchCircle,
    SketchArc,
    SketchEllipse,
    SketchSpline,
)
SketchEntity = SketchLine | SketchCircle | SketchArc | SketchEllipse | SketchSpline
SketchReference = SketchPoint | SketchEntity


@register_model_type("sketch_constraint")
@dataclass(kw_only=True)
class SketchConstraint(SketchObject):
    """One geometric or dimensional constraint over concrete sketch objects."""

    id: str = field(default_factory=lambda: _uid("skc"))
    kind: SketchConstraintKind = SketchConstraintKind.COINCIDENT
    refs: tuple[SketchReference, ...] = ()
    value: float | None = None
    driving: bool = True
    name: str = ""

    def __post_init__(self):
        self.kind = SketchConstraintKind.coerce(self.kind)
        self.refs = tuple(self.refs)
        for ref in self.refs:
            if not isinstance(ref, (SketchPoint, *SKETCH_ENTITY_TYPES)):
                raise TypeError(
                    "SketchConstraint.refs must contain SketchPoint or "
                    f"sketch entity objects, got {type(ref).__name__}"
                )
        if self.value is not None:
            self.value = float(self.value)

    def __setattr__(self, name, value):
        if name == "kind":
            value = SketchConstraintKind.coerce(value)
        elif name == "refs":
            value = tuple(value or ())
        super().__setattr__(name, value)


@register_model_type("sketch_definition")
@dataclass
class SketchDefinition:
    """Editable sketch graph in its local XY plane.

    Ownership is explicit: ``points`` and ``entities`` own the objects;
    topology and constraints point at those exact objects. No point/entity ID
    is used as an in-memory cross-object relationship.
    """

    # Direct-object identities are local to one sketch. Duplicating a Part may
    # retain local point/entity IDs without creating project-wide collisions.
    __model_identity_scope__ = True

    points: list[SketchPoint] = field(default_factory=list)
    entities: list[SketchEntity] = field(default_factory=list)
    constraints: list[SketchConstraint] = field(default_factory=list)
    grid_spacing: float = 10.0
    snap_grid: bool = True
    snap_geometry: bool = True

    def __post_init__(self):
        self.points = list(self.points)
        self.entities = list(self.entities)
        self.constraints = list(self.constraints)
        self.grid_spacing = max(abs(float(self.grid_spacing)), 1.0e-9)
        self.validate_references()

    def point_map(self) -> dict[str, SketchPoint]:
        return {point.id: point for point in self.points}

    def entity_map(self) -> dict[str, SketchEntity]:
        return {entity.id: entity for entity in self.entities}

    def point(self, point_or_id: SketchPoint | str) -> SketchPoint:
        if isinstance(point_or_id, SketchPoint):
            return point_or_id
        try:
            return self.point_map()[str(point_or_id)]
        except KeyError as exc:
            raise KeyError(f"Unknown sketch point: {point_or_id}") from exc

    def entity(self, entity_or_id: SketchEntity | str) -> SketchEntity:
        if isinstance(entity_or_id, SKETCH_ENTITY_TYPES):
            return entity_or_id
        try:
            return self.entity_map()[str(entity_or_id)]
        except KeyError as exc:
            raise KeyError(f"Unknown sketch entity: {entity_or_id}") from exc

    def validate_references(self) -> None:
        """Reject dangling/copied topology objects and duplicate persistent IDs."""

        point_ids: dict[str, SketchPoint] = {}
        point_objects = {id(point) for point in self.points}
        for point in self.points:
            if not isinstance(point, SketchPoint):
                raise TypeError("SketchDefinition.points must contain SketchPoint objects")
            previous = point_ids.get(point.id)
            if previous is not None and previous is not point:
                raise ValueError(f"Duplicate sketch point id '{point.id}'")
            point_ids[point.id] = point

        entity_ids: dict[str, SketchEntity] = {}
        entity_objects: set[int] = set()
        for entity in self.entities:
            if not isinstance(entity, SKETCH_ENTITY_TYPES):
                raise TypeError(
                    "SketchDefinition.entities contains unsupported "
                    f"{type(entity).__name__}"
                )
            previous = entity_ids.get(entity.id)
            if previous is not None and previous is not entity:
                raise ValueError(f"Duplicate sketch entity id '{entity.id}'")
            entity_ids[entity.id] = entity
            entity_objects.add(id(entity))
            for point in entity_points(entity):
                if id(point) not in point_objects:
                    raise ValueError(
                        f"Sketch entity '{entity.id}' references a point not owned "
                        "by its SketchDefinition"
                    )

        constraint_ids: set[str] = set()
        for constraint in self.constraints:
            if not isinstance(constraint, SketchConstraint):
                raise TypeError(
                    "SketchDefinition.constraints must contain SketchConstraint objects"
                )
            if constraint.id in constraint_ids:
                raise ValueError(f"Duplicate sketch constraint id '{constraint.id}'")
            constraint_ids.add(constraint.id)
            for ref in constraint.refs:
                if isinstance(ref, SketchPoint):
                    valid = id(ref) in point_objects
                else:
                    valid = id(ref) in entity_objects
                if not valid:
                    raise ValueError(
                        f"Sketch constraint '{constraint.id}' references an object "
                        "not owned by its SketchDefinition"
                    )

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
        entity = SketchLine(start=p1, end=p2, construction=construction)
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
            center=point,
            radius=radius,
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
            center=pc,
            start=ps,
            end=pe,
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
            center=pc,
            major=pm,
            minor_radius=minor_radius,
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
        points = tuple(
            self.add_point(*xy, construction=construction)
            for xy in coordinates
        )
        entity = SketchSpline(
            points=points,
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
        for entity in self.entities:
            if isinstance(entity, SketchCircle):
                center = entity.center
                r = abs(float(entity.radius))
                xs.extend((center.x - r, center.x + r))
                ys.extend((center.y - r, center.y + r))
            elif isinstance(entity, SketchEllipse):
                center = entity.center
                major = entity.major
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
    mode: SketchFeatureMode = SketchFeatureMode.EXTRUSION
    operation: SketchBooleanOperation = SketchBooleanOperation.NEW
    sketch: SketchDefinition = field(default_factory=SketchDefinition)
    depth: float = 10.0
    angle_degrees: float = 360.0
    symmetric: bool = False
    reverse: bool = False
    revolve_axis: SketchAxis = SketchAxis.X

    def __post_init__(self):
        super().__post_init__()
        self.mode = SketchFeatureMode.coerce(self.mode)
        self.operation = SketchBooleanOperation.coerce(self.operation)
        self.depth = max(abs(float(self.depth)), 1.0e-9)
        self.angle_degrees = max(
            min(abs(float(self.angle_degrees)), 360.0), 1.0e-6
        )
        self.revolve_axis = SketchAxis.coerce(self.revolve_axis)
        if not isinstance(self.sketch, SketchDefinition):
            raise TypeError("SketchFeature.sketch must be a SketchDefinition")

    def __setattr__(self, name, value):
        if name == "mode":
            value = SketchFeatureMode.coerce(value)
        elif name == "operation":
            value = SketchBooleanOperation.coerce(value)
        elif name == "revolve_axis":
            value = SketchAxis.coerce(value)
        super().__setattr__(name, value)


def entity_points(entity: SketchEntity) -> tuple[SketchPoint, ...]:
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


def _require_points(*points) -> None:
    for point in points:
        if not isinstance(point, SketchPoint):
            raise TypeError(
                "Sketch topology requires SketchPoint objects, not "
                f"{type(point).__name__}"
            )


__all__ = [
    "SketchObject",
    "SketchPoint",
    "SketchLine",
    "SketchCircle",
    "SketchArc",
    "SketchEllipse",
    "SketchSpline",
    "SketchEntity",
    "SketchReference",
    "SketchConstraintKind",
    "SketchConstraint",
    "SketchDefinition",
    "SketchFeatureMode",
    "SketchBooleanOperation",
    "SketchAxis",
    "SketchFeature",
    "SKETCH_ENTITY_TYPES",
    "entity_points",
]
