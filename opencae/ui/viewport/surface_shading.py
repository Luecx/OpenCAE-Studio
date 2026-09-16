from __future__ import annotations

import numpy as np

from opencae.ui.core.theme import PALETTE

_LIGHT = np.asarray((0.35, -0.45, 0.82), dtype=float)
_LIGHT /= np.linalg.norm(_LIGHT)


def face_color(classification: str | None):
    """Return the active scheme's semantic CAD/meshability face color."""
    if classification == "regular":
        return PALETTE["meshability_regular"]
    if classification == "irregular":
        return PALETTE["meshability_irregular"]
    return PALETTE["cad_face"]


def supports_surface_shading(mesh) -> bool:
    """Return whether *mesh* contains polygon cells with meaningful normals.

    PyVista cannot compute normals for point clouds or line-only PolyData. Those
    datasets are valid OpenCAE display meshes for authored nodes, trusses, and
    beams, so callers must treat normal-based lighting as an optional surface
    feature rather than a universal mesh property.
    """
    try:
        faces = getattr(mesh, "faces", None)
        return faces is not None and bool(np.asarray(faces).size)
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return False


def mesh_cell_colors(mesh):
    """Return stable per-cell RGB colors for surfaces, lines, and point cells."""
    cell_count = int(getattr(mesh, "n_cells", 0) or 0)
    if cell_count <= 0:
        return np.empty((0, 3), dtype=np.uint8)

    base = _rgb(PALETTE["mesh_surface"])
    normals = _cell_normals(mesh, cell_count)
    if normals is None:
        # Line and vertex cells have no surface normal. Keep their appearance
        # deterministic instead of asking PyVista to synthesize impossible
        # polygon normals (which raises for beam/truss meshes).
        return _constant_colors(base, cell_count)

    norms = np.linalg.norm(normals, axis=1)
    normalized = normals / np.maximum(norms[:, None], 1.0e-14)
    directional = 0.90 + 0.10 * np.abs(normalized @ _LIGHT)
    colors = np.clip(base[None, :] * directional[:, None], 0.12, 0.96)
    return np.asarray(np.rint(colors * 255.0), dtype=np.uint8)


def _cell_normals(mesh, cell_count: int) -> np.ndarray | None:
    try:
        normals = np.asarray(mesh.cell_data["Normals"], dtype=float)
    except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
        normals = None

    if _valid_normals(normals, cell_count):
        return normals
    if not supports_surface_shading(mesh):
        return None

    try:
        computed = mesh.compute_normals(
            cell_normals=True,
            point_normals=False,
            consistent_normals=True,
            inplace=False,
        )
        normals = np.asarray(computed.cell_data["Normals"], dtype=float)
    except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
        return None
    return normals if _valid_normals(normals, cell_count) else None


def _valid_normals(normals, cell_count: int) -> bool:
    return bool(
        normals is not None
        and getattr(normals, "ndim", 0) == 2
        and normals.shape == (cell_count, 3)
        and np.all(np.isfinite(normals))
    )


def _constant_colors(base: np.ndarray, cell_count: int) -> np.ndarray:
    colors = np.clip(np.repeat(base[None, :], cell_count, axis=0), 0.12, 0.96)
    return np.asarray(np.rint(colors * 255.0), dtype=np.uint8)


def _rgb(color: str) -> np.ndarray:
    value = str(color).strip().lstrip("#")
    if len(value) != 6:
        return np.asarray((0.5, 0.58, 0.64), dtype=float)
    return np.asarray(
        [int(value[index:index + 2], 16) / 255.0 for index in (0, 2, 4)],
        dtype=float,
    )
