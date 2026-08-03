from __future__ import annotations

import numpy as np

REGULAR = "regular"
IRREGULAR = "irregular"


# The classifier is deliberately conservative.  It recognises cells that can
# be represented as a translational sweep between two cap *sets*.  A cap set
# may contain several coplanar OCC faces: partitioning and imported CAD often
# split one geometric end face into multiple surface patches.
def classify_cells(snapshot) -> dict[int, str]:
    patches = {int(patch.tag): patch for patch in snapshot.surfaces}
    cell_surfaces: dict[int, list[int]] = {
        int(cell): [] for cell in snapshot.entities.get(3, ())
    }
    for surface_tag, cells in snapshot.surface_to_cells.items():
        for cell in cells:
            cell_surfaces.setdefault(int(cell), []).append(int(surface_tag))

    result: dict[int, str] = {}
    diagonal = _bounds_diagonal(snapshot.bounds)
    tolerance = max(diagonal * 1.0e-5, 1.0e-9)
    for cell, surface_tags in cell_surfaces.items():
        cell_patches = [patches[tag] for tag in surface_tags if tag in patches]
        result[cell] = REGULAR if _looks_extruded(cell_patches, tolerance) else IRREGULAR
    return result


def oriented_faces(snapshot, patch) -> np.ndarray:
    """Return patch faces with a stable body-consistent orientation."""
    faces = np.asarray(patch.faces, dtype=np.int64).copy()
    normal = patch_normal(patch.points, faces)
    if normal is None:
        return faces
    adjacent = tuple(int(value) for value in snapshot.surface_to_cells.get(int(patch.tag), ()))
    flip = False
    if len(adjacent) == 1:
        center = np.mean(np.asarray(patch.points, dtype=float), axis=0)
        cell_center = _cell_center(snapshot, adjacent[0])
        if cell_center is not None and float(np.dot(normal, center - cell_center)) < 0.0:
            flip = True
    else:
        # Internal faces have no unique outward side. Use a deterministic sign
        # so partition-created coplanar patches cannot randomly alternate.
        index = int(np.argmax(np.abs(normal)))
        flip = bool(normal[index] < 0.0)
    return _reverse_faces(faces) if flip else faces


def surface_classification(snapshot, surface_tag: int) -> str:
    values = [
        snapshot.cell_meshability.get(int(cell), IRREGULAR)
        for cell in snapshot.surface_to_cells.get(int(surface_tag), ())
    ]
    return REGULAR if values and all(value == REGULAR for value in values) else IRREGULAR


def patch_normal(points, faces) -> np.ndarray | None:
    points = np.asarray(points, dtype=float)
    faces = np.asarray(faces, dtype=np.int64).ravel()
    total = np.zeros(3, dtype=float)
    cursor = 0
    while cursor < len(faces):
        count = int(faces[cursor])
        indices = faces[cursor + 1:cursor + 1 + count]
        cursor += count + 1
        if count < 3:
            continue
        base = points[int(indices[0])]
        for index in range(1, count - 1):
            total += np.cross(
                points[int(indices[index])] - base,
                points[int(indices[index + 1])] - base,
            )
    norm = float(np.linalg.norm(total))
    return total / norm if norm > 1.0e-14 else None


def _looks_extruded(patches, tolerance: float) -> bool:
    if len(patches) < 3:
        return False

    metrics = [_surface_metrics(patch) for patch in patches]
    planar = [item for item in metrics if item["planar"] and item["normal"] is not None]
    if len(planar) < 2:
        return False

    # Imported/partitioned B-reps commonly represent one sweep cap with
    # several coplanar ADVANCED_FACE entities.  Candidate directions are thus
    # based on normal clusters, not on pairs of individually area-matched faces.
    for direction in _candidate_directions(planar):
        if _is_sweep_along(metrics, direction, tolerance):
            return True
    return False


def _candidate_directions(planar) -> list[np.ndarray]:
    candidates: list[np.ndarray] = []
    for item in planar:
        direction = _canonical_direction(item["normal"])
        if direction is None:
            continue
        if any(abs(float(np.dot(direction, current))) > 0.995 for current in candidates):
            continue
        candidates.append(direction)
    return candidates


def _canonical_direction(value) -> np.ndarray | None:
    direction = np.asarray(value, dtype=float).reshape(-1)
    if len(direction) < 3:
        return None
    direction = direction[:3]
    norm = float(np.linalg.norm(direction))
    if norm <= 1.0e-14:
        return None
    direction = direction / norm
    axis = int(np.argmax(np.abs(direction)))
    return -direction if direction[axis] < 0.0 else direction


def _is_sweep_along(metrics, direction: np.ndarray, tolerance: float) -> bool:
    projections = [np.asarray(item["points"], dtype=float) @ direction for item in metrics]
    finite = [values[np.isfinite(values)] for values in projections if len(values)]
    if not finite:
        return False
    all_values = np.concatenate(finite)
    lower = float(np.min(all_values))
    upper = float(np.max(all_values))
    height = upper - lower
    if height <= tolerance:
        return False

    level_tolerance = max(tolerance * 2.0, height * 0.0125)
    lower_caps = []
    upper_caps = []

    for item, values in zip(metrics, projections):
        if len(values) == 0 or not np.all(np.isfinite(values)):
            return False
        span = float(np.ptp(values))
        normal = item["normal"]
        parallel = bool(
            item["planar"]
            and normal is not None
            and abs(float(np.dot(normal, direction))) >= 0.965
        )

        # All points of a cap patch must lie on one extreme level.  This allows
        # several coplanar fragments at either end while still rejecting an
        # unpartitioned body with an intermediate indentation face.
        if parallel and float(np.max(np.abs(values - lower))) <= level_tolerance:
            lower_caps.append(item)
            continue
        if parallel and float(np.max(np.abs(values - upper))) <= level_tolerance:
            upper_caps.append(item)
            continue

        # Every non-cap boundary must connect both cap levels.  A planar face
        # normal to the sweep direction at an intermediate level therefore
        # makes the original, unsplit hook cell irregular; after partitioning
        # that same face becomes an end cap of one of the resulting cells.
        if span < height * 0.80:
            return False
        if float(np.min(values)) > lower + level_tolerance:
            return False
        if float(np.max(values)) < upper - level_tolerance:
            return False

    if not lower_caps or not upper_caps:
        return False

    lower_area = sum(float(item["area"]) for item in lower_caps)
    upper_area = sum(float(item["area"]) for item in upper_caps)
    if lower_area <= 1.0e-14 or upper_area <= 1.0e-14:
        return False
    area_ratio = abs(lower_area - upper_area) / max(lower_area, upper_area)
    return area_ratio <= 0.15


def _surface_metrics(patch):
    points = np.asarray(patch.points, dtype=float)
    center = np.mean(points, axis=0)
    centered = points - center
    planar = False
    if len(points) >= 3:
        _u, singular, vh = np.linalg.svd(centered, full_matrices=False)
        scale = float(singular[0]) if len(singular) else 0.0
        planar = bool(scale > 1.0e-14 and singular[-1] / scale < 2.0e-3)
        fit_normal = vh[-1] if len(vh) >= 3 else None
    else:
        fit_normal = None
    normal = patch_normal(points, patch.faces)
    if normal is None and fit_normal is not None:
        norm = float(np.linalg.norm(fit_normal))
        normal = fit_normal / norm if norm > 1.0e-14 else None
    return {
        "points": points,
        "center": center,
        "normal": normal,
        "planar": planar,
        "area": _surface_area(points, patch.faces),
    }


def _surface_area(points, faces) -> float:
    area = 0.0
    values = np.asarray(faces, dtype=np.int64).ravel()
    cursor = 0
    while cursor < len(values):
        count = int(values[cursor])
        indices = values[cursor + 1:cursor + 1 + count]
        cursor += count + 1
        if count < 3:
            continue
        base = points[int(indices[0])]
        for index in range(1, count - 1):
            area += 0.5 * float(np.linalg.norm(np.cross(
                points[int(indices[index])] - base,
                points[int(indices[index + 1])] - base,
            )))
    return area


def _cell_center(snapshot, cell: int):
    points = []
    for patch in snapshot.surfaces:
        if int(cell) in {int(value) for value in snapshot.surface_to_cells.get(int(patch.tag), ())}:
            points.append(np.asarray(patch.points, dtype=float))
    if not points:
        return None
    return np.mean(np.vstack(points), axis=0)


def _reverse_faces(faces):
    result = []
    cursor = 0
    values = np.asarray(faces, dtype=np.int64).ravel()
    while cursor < len(values):
        count = int(values[cursor])
        indices = list(values[cursor + 1:cursor + 1 + count])
        result.extend((count, *reversed(indices)))
        cursor += count + 1
    return np.asarray(result, dtype=np.int64)


def _bounds_diagonal(bounds) -> float:
    if not bounds:
        return 1.0
    values = np.asarray(bounds, dtype=float)
    return float(np.linalg.norm(values[3:] - values[:3]))
