from __future__ import annotations

import numpy as np

_BASE = np.asarray((0.50, 0.58, 0.64), dtype=float)
_LIGHT = np.asarray((0.35, -0.45, 0.82), dtype=float)
_LIGHT /= np.linalg.norm(_LIGHT)


def face_color(mesh, tag: int):
    """Return a stable orientation-dependent color without cast shadows."""
    try:
        normals = mesh.compute_normals(
            cell_normals=True, point_normals=False, inplace=False,
        ).cell_data["Normals"]
        normal = np.asarray(normals, dtype=float).mean(axis=0)
        norm = float(np.linalg.norm(normal))
        if norm > 1.0e-12:
            normal /= norm
            directional = 0.62 + 0.30 * abs(float(np.dot(normal, _LIGHT)))
        else:
            directional = 0.78
    except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
        directional = 0.74 + 0.03 * ((tag % 5) - 2)
    tint = 0.018 * ((tag % 7) - 3)
    return tuple(np.clip(_BASE * directional + tint, 0.18, 0.92))


def mesh_cell_colors(mesh):
    """Return stable per-cell RGB shading for a triangulated mesh surface."""
    try:
        normals = np.asarray(mesh.cell_data["Normals"], dtype=float)
    except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
        normals = mesh.compute_normals(
            cell_normals=True, point_normals=False, inplace=False,
        ).cell_data["Normals"]
    norms = np.linalg.norm(normals, axis=1)
    normalized = normals / np.maximum(norms[:, None], 1.0e-14)
    directional = 0.58 + 0.34 * np.abs(normalized @ _LIGHT)
    colors = np.clip(_BASE[None, :] * directional[:, None], 0.18, 0.92)
    return np.asarray(np.rint(colors * 255.0), dtype=np.uint8)
