from __future__ import annotations

import numpy as np

REGULAR_COLOR = "#7895a3"
IRREGULAR_COLOR = "#8b8793"
DEFAULT_COLOR = "#7f8d99"

_BASE = np.asarray((0.50, 0.58, 0.64), dtype=float)
_LIGHT = np.asarray((0.35, -0.45, 0.82), dtype=float)
_LIGHT /= np.linalg.norm(_LIGHT)


def face_color(classification: str | None):
    if classification == "regular":
        return REGULAR_COLOR
    if classification == "irregular":
        return IRREGULAR_COLOR
    return DEFAULT_COLOR


def mesh_cell_colors(mesh):
    """Return stable per-cell RGB shading for a triangulated mesh surface."""
    try:
        normals = np.asarray(mesh.cell_data["Normals"], dtype=float)
    except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
        normals = mesh.compute_normals(
            cell_normals=True, point_normals=False, consistent_normals=True,
            inplace=False,
        ).cell_data["Normals"]
    norms = np.linalg.norm(normals, axis=1)
    normalized = normals / np.maximum(norms[:, None], 1.0e-14)
    directional = 0.58 + 0.34 * np.abs(normalized @ _LIGHT)
    colors = np.clip(_BASE[None, :] * directional[:, None], 0.18, 0.92)
    return np.asarray(np.rint(colors * 255.0), dtype=np.uint8)
