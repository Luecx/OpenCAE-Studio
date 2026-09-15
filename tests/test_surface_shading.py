from __future__ import annotations

import numpy as np
import pyvista as pv

from opencae.ui.viewport.surface_shading import (
    mesh_cell_colors,
    supports_surface_shading,
)


def test_line_polydata_uses_flat_cell_colors_without_normals():
    mesh = pv.PolyData(np.asarray(((0.0, 0.0, 0.0), (1.0, 0.0, 0.0))))
    mesh.lines = np.asarray((2, 0, 1), dtype=np.int64)

    assert supports_surface_shading(mesh) is False
    colors = mesh_cell_colors(mesh)

    assert colors.shape == (1, 3)
    assert colors.dtype == np.uint8


def test_polygon_polydata_keeps_normal_based_surface_shading():
    mesh = pv.PolyData(
        np.asarray(
            (
                (0.0, 0.0, 0.0),
                (1.0, 0.0, 0.0),
                (0.0, 1.0, 0.0),
            )
        ),
        faces=np.asarray((3, 0, 1, 2), dtype=np.int64),
    )

    assert supports_surface_shading(mesh) is True
    colors = mesh_cell_colors(mesh)

    assert colors.shape == (1, 3)
    assert colors.dtype == np.uint8


def test_point_cloud_cell_colors_do_not_attempt_normal_generation():
    mesh = pv.PolyData(np.asarray(((0.0, 0.0, 0.0),)))

    assert supports_surface_shading(mesh) is False
    colors = mesh_cell_colors(mesh)

    assert colors.shape == (1, 3)
    assert colors.dtype == np.uint8
