from __future__ import annotations

import numpy as np
import pyvista as pv

from opencae.ui.other.viewport.result_visualization import _supports_result_shading
from opencae.ui.other.viewport.surface_shading import (
    mesh_cell_colors,
    supports_surface_shading,
)


def test_line_polydata_uses_flat_cell_colors_without_normals():
    mesh = pv.PolyData(np.asarray(((0.0, 0.0, 0.0), (1.0, 0.0, 0.0))))
    mesh.lines = np.asarray((2, 0, 1), dtype=np.int64)

    assert supports_surface_shading(mesh) is False
    colors = mesh_cell_colors(mesh)

    # PyVista versions differ in whether PolyData(points) retains implicit
    # vertex cells after lines are assigned. The rendering contract is one RGB
    # row per actual cell, independent of that representation detail.
    assert colors.shape == (mesh.n_cells, 3)
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


def test_solution_line_grid_disables_surface_shading():
    grid = pv.UnstructuredGrid(
        np.asarray((2, 0, 1), dtype=np.int64),
        np.asarray((pv.CellType.LINE,), dtype=np.uint8),
        np.asarray(((0.0, 0.0, 0.0), (1.0, 0.0, 0.0))),
    )

    assert _supports_result_shading(grid) is False


def test_solution_surface_grid_keeps_surface_shading():
    grid = pv.UnstructuredGrid(
        np.asarray((3, 0, 1, 2), dtype=np.int64),
        np.asarray((pv.CellType.TRIANGLE,), dtype=np.uint8),
        np.asarray(
            (
                (0.0, 0.0, 0.0),
                (1.0, 0.0, 0.0),
                (0.0, 1.0, 0.0),
            )
        ),
    )

    assert _supports_result_shading(grid) is True
