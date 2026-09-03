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


def mesh_cell_colors(mesh):
    """Return stable per-cell RGB shading based on the active mesh surface token."""
    try:
        normals = np.asarray(mesh.cell_data["Normals"], dtype=float)
    except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
        normals = mesh.compute_normals(
            cell_normals=True,
            point_normals=False,
            consistent_normals=True,
            inplace=False,
        ).cell_data["Normals"]
    norms = np.linalg.norm(normals, axis=1)
    normalized = normals / np.maximum(norms[:, None], 1.0e-14)
    directional = 0.90 + 0.10 * np.abs(normalized @ _LIGHT)
    base = _rgb(PALETTE["mesh_surface"])
    colors = np.clip(base[None, :] * directional[:, None], 0.12, 0.96)
    return np.asarray(np.rint(colors * 255.0), dtype=np.uint8)


def _rgb(color: str) -> np.ndarray:
    value = str(color).strip().lstrip("#")
    if len(value) != 6:
        return np.asarray((0.5, 0.58, 0.64), dtype=float)
    return np.asarray(
        [int(value[index:index + 2], 16) / 255.0 for index in (0, 2, 4)],
        dtype=float,
    )
