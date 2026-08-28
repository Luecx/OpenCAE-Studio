"""Regress the filled volumetric cross-section used by Section View."""

import numpy as np
import pyvista as pv

from opencae.ui.viewport.section_view import section_cut_surface


def _hex_grid():
    points = np.asarray(
        (
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (1.0, 1.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
            (1.0, 0.0, 1.0),
            (1.0, 1.0, 1.0),
            (0.0, 1.0, 1.0),
        ),
        dtype=float,
    )
    cells = np.asarray((8, 0, 1, 2, 3, 4, 5, 6, 7), dtype=np.int64)
    grid = pv.UnstructuredGrid(
        cells,
        np.asarray((pv.CellType.HEXAHEDRON,), dtype=np.uint8),
        points,
    )
    grid.point_data["VALUE"] = points[:, 0] + 2.0 * points[:, 1]
    return grid


def test_section_view_creates_real_filled_cross_section_through_volume():
    cut = section_cut_surface(_hex_grid(), (0.5, 0.5, 0.5), (1.0, 0.0, 0.0))

    assert cut is not None
    assert cut.n_cells > 0
    assert np.allclose(cut.points[:, 0], 0.5)
    assert "VALUE" in cut.point_data

    sized = cut.compute_cell_sizes(length=False, area=True, volume=False)
    assert float(np.sum(sized.cell_data["Area"])) > 0.99


def test_section_view_does_not_fake_a_cap_for_shell_only_geometry():
    shell = pv.Plane(
        center=(0.0, 0.0, 0.0),
        direction=(0.0, 0.0, 1.0),
        i_size=2.0,
        j_size=2.0,
    )
    cut = section_cut_surface(shell, (0.0, 0.0, 0.0), (1.0, 0.0, 0.0))

    assert cut is None
