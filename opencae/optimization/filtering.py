from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.sparse import csr_matrix, identity
from scipy.spatial import cKDTree

from opencae.model.entities.optimization import (
    SymmetryType,
    TopologyFilterSettings,
    TopologySymmetry,
)


@dataclass(frozen=True, slots=True)
class FilterOperators:
    density_constraint: csr_matrix
    sensitivity: csr_matrix
    minimum_distance: float
    density_constraint_radius: float
    sensitivity_radius: float

    def physical_density(self, design_density: np.ndarray) -> np.ndarray:
        return np.asarray(self.density_constraint @ design_density, dtype=float).ravel()

    def sensitivity_gradient(
        self,
        raw_gradient: np.ndarray,
        physical_density: np.ndarray,
        *,
        density_weighted: bool,
        minimum_density: float,
    ) -> np.ndarray:
        raw = np.asarray(raw_gradient, dtype=float).ravel()
        density = np.asarray(physical_density, dtype=float).ravel()
        if density_weighted:
            smoothed = np.asarray(
                self.sensitivity @ (density * raw), dtype=float
            ).ravel() / np.maximum(density, float(minimum_density))
        else:
            smoothed = np.asarray(self.sensitivity @ raw, dtype=float).ravel()
        return np.asarray(self.density_constraint.T @ smoothed, dtype=float).ravel()

    def constraint_gradient(self, physical_gradient: np.ndarray) -> np.ndarray:
        return np.asarray(
            self.density_constraint.T @ np.asarray(physical_gradient, dtype=float).ravel(),
            dtype=float,
        ).ravel()


def build_filter_operators(
    centroids: np.ndarray,
    settings: TopologyFilterSettings,
    symmetries: list[TopologySymmetry] | tuple[TopologySymmetry, ...] = (),
    *,
    active_mask: np.ndarray | None = None,
) -> FilterOperators:
    all_points = np.asarray(centroids, dtype=float)
    if all_points.ndim != 2 or all_points.shape[1] != 3 or not len(all_points):
        raise ValueError("Topology filters require an N x 3 centroid array")
    active = np.ones(len(all_points), dtype=bool) if active_mask is None else np.asarray(active_mask, dtype=bool).ravel()
    if len(active) != len(all_points):
        raise ValueError("The topology-filter active mask has the wrong length")
    if not np.any(active):
        raise ValueError("The topology filter has no active design elements")
    points = all_points[active]
    minimum = minimum_element_distance(points)
    density_radius = settings.density_constraint_radius.resolved(minimum)
    sensitivity_radius = settings.sensitivity_radius.resolved(minimum)
    if settings.enabled and sensitivity_radius < density_radius:
        raise ValueError(
            "The sensitivity-filter radius must be greater than or equal to "
            "the density/constraint radius"
        )

    active_symmetries = [item for item in symmetries if item.enabled]
    active_identity = identity(len(points), dtype=float, format="csr")
    density_active = (
        build_density_constraint_matrix(
            points,
            density_radius,
            active_symmetries,
            duplicate_tolerance=max(minimum * 1.0e-6, 1.0e-10),
        )
        if settings.enabled or active_symmetries
        else active_identity
    )
    sensitivity_active = (
        build_distance_matrix(points, sensitivity_radius)
        if settings.enabled
        else active_identity
    )
    density_matrix = _embed_active_matrix(density_active, active)
    sensitivity_matrix = _embed_active_matrix(sensitivity_active, active)
    return FilterOperators(
        density_matrix,
        sensitivity_matrix,
        minimum,
        density_radius,
        sensitivity_radius,
    )


def minimum_element_distance(points: np.ndarray) -> float:
    values = np.asarray(points, dtype=float)
    if len(values) < 2:
        scale = float(np.linalg.norm(np.ptp(values, axis=0))) if len(values) else 1.0
        return max(scale, 1.0)
    distances, _indices = cKDTree(values).query(values, k=2)
    nearest = np.asarray(distances[:, 1], dtype=float)
    positive = nearest[np.isfinite(nearest) & (nearest > 1.0e-12)]
    if not len(positive):
        raise ValueError("Element centroids are coincident; an automatic filter radius cannot be determined")
    # The literal minimum positive nearest-neighbour distance is used as the
    # characteristic spacing, matching the UI wording. Near-zero duplicates
    # have already been removed by the positive tolerance above.
    return float(np.min(positive))


def build_distance_matrix(points: np.ndarray, radius: float) -> csr_matrix:
    values = np.asarray(points, dtype=float)
    radius = float(radius)
    if radius <= 0.0:
        raise ValueError("Filter radius must be positive")
    tree = cKDTree(values)
    rows: list[int] = []
    cols: list[int] = []
    data: list[float] = []
    for row, point in enumerate(values):
        neighbours = tree.query_ball_point(point, radius)
        weights = []
        for column in neighbours:
            distance = float(np.linalg.norm(point - values[column]))
            weight = max(radius - distance, 0.0)
            if weight > 0.0:
                weights.append((int(column), weight))
        if not weights:
            weights = [(row, 1.0)]
        total = sum(weight for _column, weight in weights)
        for column, weight in weights:
            rows.append(row)
            cols.append(column)
            data.append(weight / total)
    return csr_matrix((data, (rows, cols)), shape=(len(values), len(values)))


def build_density_constraint_matrix(
    points: np.ndarray,
    radius: float,
    symmetries: list[TopologySymmetry] | tuple[TopologySymmetry, ...] = (),
    *,
    duplicate_tolerance: float = 1.0e-9,
) -> csr_matrix:
    """Build the small-radius density/constraint coupling matrix.

    Every symmetry expands the centroid cloud. Each virtual point retains the
    column index of its original design element. Neighbour weights are then
    accumulated back onto those original columns. Sequential symmetries form
    the requested closure: N points become 2N for one mirror and up to 4N for
    two independent mirrors, while rotational symmetry adds all requested
    occurrences.
    """

    real = np.asarray(points, dtype=float)
    virtual = real.copy()
    sources = np.arange(len(real), dtype=np.int64)
    for symmetry in symmetries:
        transformed_points = []
        transformed_sources = []
        for operation in _symmetry_operations(symmetry):
            transformed_points.append(operation(virtual))
            transformed_sources.append(sources.copy())
        if transformed_points:
            projected_count = len(virtual) + sum(len(value) for value in transformed_points)
            if projected_count > 5_000_000:
                raise ValueError(
                    "The requested symmetry closure would create more than five million virtual points"
                )
            virtual = np.vstack((virtual, *transformed_points))
            sources = np.concatenate((sources, *transformed_sources))
            virtual, sources = _deduplicate_virtual(
                virtual,
                sources,
                duplicate_tolerance,
            )

    if symmetries and len(virtual) > len(real):
        nearest, _ = cKDTree(real).query(virtual[len(real):], k=1)
        unmatched = int(np.count_nonzero(np.asarray(nearest) > float(radius)))
        if unmatched:
            raise ValueError(
                f"Symmetry mapping could not associate {unmatched} virtual element "
                f"centroid(s) within the density/constraint radius {float(radius):.6g}"
            )

    tree = cKDTree(virtual)
    rows: list[int] = []
    cols: list[int] = []
    data: list[float] = []
    for row, point in enumerate(real):
        accumulated: dict[int, float] = {}
        for virtual_index in tree.query_ball_point(point, float(radius)):
            distance = float(np.linalg.norm(point - virtual[virtual_index]))
            weight = max(float(radius) - distance, 0.0)
            if weight <= 0.0:
                continue
            column = int(sources[virtual_index])
            accumulated[column] = accumulated.get(column, 0.0) + weight
        if not accumulated:
            accumulated[row] = 1.0
        total = sum(accumulated.values())
        for column, weight in sorted(accumulated.items()):
            rows.append(row)
            cols.append(column)
            data.append(weight / total)
    return csr_matrix((data, (rows, cols)), shape=(len(real), len(real)))


def _symmetry_operations(symmetry: TopologySymmetry):
    reference = dict(symmetry.reference or {})
    if symmetry.symmetry_type == SymmetryType.PLANAR:
        origin = _vector(reference.get("origin") or reference.get("point"), "plane origin")
        normal = _unit(reference.get("normal") or reference.get("direction"), "plane normal")

        def reflect(points):
            values = np.asarray(points, dtype=float)
            signed = (values - origin) @ normal
            return values - 2.0 * signed[:, None] * normal[None, :]

        return (reflect,)

    origin = _vector(reference.get("origin") or reference.get("point"), "rotation-axis origin")
    axis = _unit(reference.get("direction"), "rotation-axis direction")
    operations = []
    for index in range(1, int(symmetry.occurrences)):
        angle = 2.0 * np.pi * index / int(symmetry.occurrences)
        rotation = _rodrigues(axis, angle)

        def rotate(points, matrix=rotation):
            values = np.asarray(points, dtype=float)
            return (matrix @ (values - origin).T).T + origin

        operations.append(rotate)
    return tuple(operations)


def _deduplicate_virtual(points, sources, tolerance):
    tolerance = max(float(tolerance), 1.0e-14)
    keys = np.rint(np.asarray(points, dtype=float) / tolerance).astype(np.int64)
    keep = []
    seen = set()
    # Source participates in the key: coincident images of different design
    # elements must both contribute to the coupling weights.
    for index, (key, source) in enumerate(zip(keys, sources)):
        marker = (int(source), int(key[0]), int(key[1]), int(key[2]))
        if marker in seen:
            continue
        seen.add(marker)
        keep.append(index)
    return np.asarray(points, dtype=float)[keep], np.asarray(sources, dtype=np.int64)[keep]


def _rodrigues(axis, angle):
    x, y, z = axis
    cross = np.asarray(((0.0, -z, y), (z, 0.0, -x), (-y, x, 0.0)))
    identity = np.eye(3)
    return identity * np.cos(angle) + (1.0 - np.cos(angle)) * np.outer(axis, axis) + np.sin(angle) * cross


def _vector(value, label):
    if value is None:
        raise ValueError(f"Topology symmetry has no {label}")
    result = np.asarray(value, dtype=float)
    if result.shape != (3,) or not np.all(np.isfinite(result)):
        raise ValueError(f"Topology symmetry has an invalid {label}")
    return result


def _unit(value, label):
    result = _vector(value, label)
    norm = float(np.linalg.norm(result))
    if norm <= 1.0e-14:
        raise ValueError(f"Topology symmetry has a zero {label}")
    return result / norm


def _embed_active_matrix(matrix: csr_matrix, active_mask: np.ndarray) -> csr_matrix:
    active = np.asarray(active_mask, dtype=bool).ravel()
    active_rows = np.flatnonzero(active)
    inactive_rows = np.flatnonzero(~active)
    coo = matrix.tocoo()
    rows = [int(active_rows[row]) for row in coo.row]
    cols = [int(active_rows[col]) for col in coo.col]
    data = [float(value) for value in coo.data]
    rows.extend(int(value) for value in inactive_rows)
    cols.extend(int(value) for value in inactive_rows)
    data.extend(1.0 for _ in inactive_rows)
    return csr_matrix((data, (rows, cols)), shape=(len(active), len(active)))
