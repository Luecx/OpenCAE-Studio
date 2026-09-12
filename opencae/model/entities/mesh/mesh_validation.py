"""Local geometric validity checks for editable first-order finite elements."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from ..fem import Node
from .mesh_lifecycle import MeshValidity
from .mesh_quality import MeshQualitySummary


@dataclass(frozen=True, slots=True)
class ElementValidationResult:
    element_id: int
    signed_measure: float
    minimum_edge: float
    maximum_edge: float
    quality: float
    inverted: bool = False
    degenerate: bool = False
    collapsed: bool = False

    @property
    def valid(self) -> bool:
        return not (self.inverted or self.degenerate or self.collapsed)


@dataclass(frozen=True, slots=True)
class MeshValidationReport:
    elements: tuple[ElementValidationResult, ...]

    @property
    def invalid_ids(self) -> tuple[int, ...]:
        return tuple(item.element_id for item in self.elements if not item.valid)

    @property
    def inverted_ids(self) -> tuple[int, ...]:
        return tuple(item.element_id for item in self.elements if item.inverted)

    @property
    def degenerate_ids(self) -> tuple[int, ...]:
        return tuple(item.element_id for item in self.elements if item.degenerate)

    @property
    def minimum_quality(self) -> float | None:
        values = [item.quality for item in self.elements]
        return min(values) if values else None

    @property
    def mean_quality(self) -> float | None:
        values = [item.quality for item in self.elements]
        return sum(values) / len(values) if values else None


def validate_element(element, *, tolerance=1e-12) -> ElementValidationResult:
    """Check orientation, degeneracy and collapsed edges of one linear element."""
    points = [
        tuple(float(value) for value in node.coordinates)
        for node in element.nodes
    ]
    name = type(element).__name__
    edges = _edges_for(name, len(points))
    lengths = [_distance(points[a], points[b]) for a, b in edges]
    minimum_edge = min(lengths, default=0.0)
    maximum_edge = max(lengths, default=0.0)
    scale = max(maximum_edge, 1.0)
    collapsed = bool(lengths and minimum_edge <= tolerance * scale)

    signed_measure = _signed_measure(name, points)
    solid = name in {"Tet4", "Pyramid5", "Wedge6", "Hex8"}
    exponent = 3 if solid else 2
    measure_tolerance = tolerance * max(scale**exponent, 1.0)
    degenerate = (
        abs(signed_measure) <= measure_tolerance
        if len(points) >= 3
        else collapsed
    )
    inverted = bool(solid and signed_measure < -measure_tolerance)
    edge_quality = (
        minimum_edge / maximum_edge if maximum_edge > 0.0 else 0.0
    )
    quality = (
        0.0
        if (degenerate or collapsed or inverted)
        else max(0.0, min(1.0, edge_quality))
    )
    return ElementValidationResult(
        int(element.id),
        float(signed_measure),
        float(minimum_edge),
        float(maximum_edge),
        float(quality),
        inverted,
        degenerate,
        collapsed,
    )


def validate_mesh(mesh, *, tolerance=1e-12, update=True) -> MeshValidationReport:
    """Validate all current elements and optionally update mesh lifecycle state."""
    report = MeshValidationReport(
        tuple(
            validate_element(element, tolerance=tolerance)
            for element in mesh.iter_elements()
        )
    )
    if update:
        mesh.quality = MeshQualitySummary(
            minimum=report.minimum_quality,
            mean=report.mean_quality,
            invalid_element_ids=report.invalid_ids,
            inverted_element_ids=report.inverted_ids,
            degenerate_element_ids=report.degenerate_ids,
        )
        mesh.lifecycle.validity = (
            MeshValidity.INVALID
            if report.invalid_ids
            else MeshValidity.CURRENT
        )
    return report


def validate_node_move(
    mesh,
    node_id: int,
    coordinates,
    *,
    tolerance=1e-12,
) -> MeshValidationReport:
    """Validate incident elements for a proposed node move without mutation."""
    replacement = Node(
        int(node_id),
        tuple(coordinates),
        mesh.node(node_id).origin,
    )
    results = []
    for element_id in mesh.incident_element_ids(node_id):
        element = mesh.element(element_id)
        nodes = tuple(
            replacement if node.id == int(node_id) else node
            for node in element.nodes
        )
        candidate = type(element)(element.id, nodes, element.origin)
        results.append(validate_element(candidate, tolerance=tolerance))
    return MeshValidationReport(tuple(results))


def apply_local_validation(mesh, report: MeshValidationReport) -> None:
    """Merge validation of a changed element subset into diagnostics."""
    checked = {item.element_id for item in report.elements}
    invalid = (
        set(mesh.quality.invalid_element_ids) - checked
    ) | set(report.invalid_ids)
    inverted = (
        set(mesh.quality.inverted_element_ids) - checked
    ) | set(report.inverted_ids)
    degenerate = (
        set(mesh.quality.degenerate_element_ids) - checked
    ) | set(report.degenerate_ids)
    mesh.quality.minimum = None
    mesh.quality.mean = None
    mesh.quality.invalid_element_ids = tuple(sorted(invalid))
    mesh.quality.inverted_element_ids = tuple(sorted(inverted))
    mesh.quality.degenerate_element_ids = tuple(sorted(degenerate))
    mesh.lifecycle.validity = (
        MeshValidity.INVALID if invalid else MeshValidity.CURRENT
    )


def forget_element_validation(mesh, element_id: int) -> None:
    """Remove one deleted element from cached invalidity diagnostics."""
    element_id = int(element_id)
    mesh.quality.invalid_element_ids = tuple(
        value
        for value in mesh.quality.invalid_element_ids
        if value != element_id
    )
    mesh.quality.inverted_element_ids = tuple(
        value
        for value in mesh.quality.inverted_element_ids
        if value != element_id
    )
    mesh.quality.degenerate_element_ids = tuple(
        value
        for value in mesh.quality.degenerate_element_ids
        if value != element_id
    )
    if (
        not mesh.quality.invalid_element_ids
        and mesh.lifecycle.validity is MeshValidity.INVALID
    ):
        mesh.lifecycle.validity = MeshValidity.CURRENT


def suggested_orientation_repair(element) -> tuple[int, ...] | None:
    """Return a conservative connectivity flip for an inverted solid."""
    if type(element).__name__ not in {
        "Tet4",
        "Pyramid5",
        "Wedge6",
        "Hex8",
    }:
        return None
    if not validate_element(element).inverted:
        return None
    values = list(element.connectivity)
    if len(values) < 2:
        return None
    values[0], values[1] = values[1], values[0]
    return tuple(values)


def _signed_measure(name: str, points) -> float:
    if name in {"Line2", "Beam2", "Truss2"}:
        return _distance(points[0], points[1]) if len(points) >= 2 else 0.0
    if name in {"ShellTri3", "PlaneTri3"}:
        return _triangle_area(points[0], points[1], points[2])
    if name in {"ShellQuad4", "PlaneQuad4"}:
        return _triangle_area(points[0], points[1], points[2]) + _triangle_area(
            points[0], points[2], points[3]
        )
    decompositions = {
        "Tet4": ((0, 1, 2, 3),),
        "Pyramid5": ((0, 1, 2, 4), (0, 2, 3, 4)),
        "Wedge6": ((0, 1, 2, 3), (1, 2, 4, 3), (2, 4, 5, 3)),
        "Hex8": (
            (0, 1, 3, 4),
            (1, 2, 3, 6),
            (1, 3, 4, 6),
            (1, 4, 5, 6),
            (3, 4, 6, 7),
        ),
    }
    tets = decompositions.get(name)
    if tets:
        return sum(
            _tet_volume(*(points[index] for index in tet))
            for tet in tets
        )
    return 0.0


def _edges_for(name: str, count: int):
    known = {
        "Line2": ((0, 1),),
        "Beam2": ((0, 1),),
        "Truss2": ((0, 1),),
        "ShellTri3": ((0, 1), (1, 2), (2, 0)),
        "PlaneTri3": ((0, 1), (1, 2), (2, 0)),
        "ShellQuad4": ((0, 1), (1, 2), (2, 3), (3, 0)),
        "PlaneQuad4": ((0, 1), (1, 2), (2, 3), (3, 0)),
        "Tet4": (
            (0, 1), (0, 2), (0, 3),
            (1, 2), (1, 3), (2, 3),
        ),
        "Pyramid5": (
            (0, 1), (1, 2), (2, 3), (3, 0),
            (0, 4), (1, 4), (2, 4), (3, 4),
        ),
        "Wedge6": (
            (0, 1), (1, 2), (2, 0),
            (3, 4), (4, 5), (5, 3),
            (0, 3), (1, 4), (2, 5),
        ),
        "Hex8": (
            (0, 1), (1, 2), (2, 3), (3, 0),
            (4, 5), (5, 6), (6, 7), (7, 4),
            (0, 4), (1, 5), (2, 6), (3, 7),
        ),
    }
    return known.get(
        name,
        tuple((index, (index + 1) % count) for index in range(count)),
    )


def _distance(a, b) -> float:
    return sqrt(
        sum((float(a[i]) - float(b[i])) ** 2 for i in range(3))
    )


def _triangle_area(a, b, c) -> float:
    ab = _sub(b, a)
    ac = _sub(c, a)
    cross = _cross(ab, ac)
    return 0.5 * sqrt(_dot(cross, cross))


def _tet_volume(a, b, c, d) -> float:
    return _dot(_sub(b, a), _cross(_sub(c, a), _sub(d, a))) / 6.0


def _sub(a, b):
    return tuple(float(a[i]) - float(b[i]) for i in range(3))


def _dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )
