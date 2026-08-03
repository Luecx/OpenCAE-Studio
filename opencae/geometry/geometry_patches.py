import logging

_LOG = logging.getLogger(__name__)

import numpy as np

from .snapshots import EdgePatch, SurfacePatch, VertexPatch


def surface_patch(gmsh, tag: int) -> SurfacePatch | None:
    node_tags, coords, _ = gmsh.model.mesh.getNodes(2, tag, True, False)
    if len(node_tags) == 0:
        return None
    points = np.asarray(coords, dtype=float).reshape(-1, 3)
    lookup = {int(node): index for index, node in enumerate(node_tags)}
    faces = _surface_faces(gmsh, tag, lookup)
    if not faces:
        return None
    return SurfacePatch(tag=tag, points=points, faces=np.asarray(faces, dtype=np.int64))


def edge_patch(gmsh, tag: int) -> EdgePatch | None:
    node_tags, coords, _ = gmsh.model.mesh.getNodes(1, tag, True, False)
    if len(node_tags) == 0:
        return None
    mesh_points = np.asarray(coords, dtype=float).reshape(-1, 3)

    # Sample the CAD parametrisation so concave/curved edges do not collapse to
    # coarse chords inside the shaded body.  Excessively dense wide-line joins
    # are visually noisy on some Intel OpenGL drivers, hence the conservative
    # upper bound and the cleanup/splitting step below.
    sample_count = max(24, min(128, len(mesh_points) * 3))
    sampled = _sample_curve(gmsh, tag, sample_count)
    if sampled is not None:
        points, lines = _clean_polyline(sampled)
        if len(points) >= 2 and len(lines) >= 3:
            return EdgePatch(tag=tag, points=points, lines=lines)

    lookup = {int(node): index for index, node in enumerate(node_tags)}
    lines = _edge_lines(gmsh, tag, lookup)
    if not lines:
        return None
    return EdgePatch(tag=tag, points=mesh_points, lines=np.asarray(lines, dtype=np.int64))


def _sample_curve(gmsh, tag: int, count: int) -> np.ndarray | None:
    try:
        lower, upper = gmsh.model.getParametrizationBounds(1, tag)
        start, stop = float(lower[0]), float(upper[0])
        if not np.isfinite(start) or not np.isfinite(stop) or start == stop:
            return None
        parameters = np.linspace(start, stop, max(2, int(count)), endpoint=True)
        points = np.asarray(
            gmsh.model.getValue(1, tag, parameters.tolist()), dtype=float
        ).reshape(-1, 3)
        if len(points) < 2 or not np.all(np.isfinite(points)):
            return None
        return points
    except Exception as exc:
        _LOG.debug("Could not sample CAD curve %s parametrically: %s", tag, exc)
        return None


def _clean_polyline(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return compact points and one or more connected VTK polyline cells.

    Periodic or trimmed CAD curves can occasionally contain a parametrisation
    jump.  Connecting across such a jump draws stray black fragments over a
    face.  We remove coincident samples and split only statistically obvious
    jumps instead of creating a chord through the model.
    """
    values = np.asarray(points, dtype=float).reshape(-1, 3)
    if len(values) < 2:
        return values, np.empty(0, dtype=np.int64)

    scale = float(np.linalg.norm(np.ptp(values, axis=0)))
    duplicate_tolerance = max(scale * 1.0e-10, 1.0e-12)
    keep = np.ones(len(values), dtype=bool)
    keep[1:] = np.linalg.norm(np.diff(values, axis=0), axis=1) > duplicate_tolerance
    values = values[keep]
    if len(values) < 2:
        return values, np.empty(0, dtype=np.int64)

    steps = np.linalg.norm(np.diff(values, axis=0), axis=1)
    positive = steps[steps > duplicate_tolerance]
    typical = float(np.median(positive)) if len(positive) else 0.0
    # The absolute term prevents valid long straight edges with few samples
    # from being split; the relative term catches periodic seam jumps.
    jump_limit = max(typical * 8.0, scale * 0.20, duplicate_tolerance * 10.0)
    breaks = {int(index + 1) for index, value in enumerate(steps) if value > jump_limit}

    cells: list[int] = []
    start = 0
    for stop in (*sorted(breaks), len(values)):
        count = stop - start
        if count >= 2:
            cells.extend((count, *range(start, stop)))
        start = stop
    return values, np.asarray(cells, dtype=np.int64)


def _surface_faces(gmsh, tag, lookup):
    faces: list[int] = []
    types, _, node_blocks = gmsh.model.mesh.getElements(2, tag)
    for element_type, node_block in zip(types, node_blocks):
        _, dim, _, num_nodes, _, primary = gmsh.model.mesh.getElementProperties(int(element_type))
        if dim != 2:
            continue
        rows = np.asarray(node_block, dtype=np.int64).reshape(-1, num_nodes)[:, :primary]
        for row in rows:
            local = [lookup.get(int(node)) for node in row]
            if any(index is None for index in local):
                continue
            _append_face(faces, local)
    return faces


def _append_face(faces, local):
    if len(local) in (3, 4):
        faces.extend((len(local), *local))
        return
    for index in range(1, len(local) - 1):
        faces.extend((3, local[0], local[index], local[index + 1]))


def _edge_lines(gmsh, tag, lookup):
    lines: list[int] = []
    types, _, node_blocks = gmsh.model.mesh.getElements(1, tag)
    for element_type, node_block in zip(types, node_blocks):
        _, dim, _, num_nodes, _, primary = gmsh.model.mesh.getElementProperties(int(element_type))
        if dim != 1:
            continue
        rows = np.asarray(node_block, dtype=np.int64).reshape(-1, num_nodes)[:, :primary]
        for row in rows:
            local = [lookup.get(int(node)) for node in row]
            if len(local) < 2 or any(index is None for index in local):
                continue
            for index in range(len(local) - 1):
                lines.extend((2, local[index], local[index + 1]))
    return lines


def vertex_patch(gmsh, tag: int) -> VertexPatch | None:
    try:
        point = np.asarray(gmsh.model.getValue(0, tag, []), dtype=float).reshape(3)
        return VertexPatch(tag=tag, point=point)
    except Exception as exc:
        _LOG.warning("Could not extract vertex patch %s: %s", tag, exc)
        return None
