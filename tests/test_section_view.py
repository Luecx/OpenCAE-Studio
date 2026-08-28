import numpy as np
import pyvista as pv

from opencae.ui.viewport.section_view import section_cut_surface


def _hexahedron():
    points = np.asarray(
        [
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (1.0, 1.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
            (1.0, 0.0, 1.0),
            (1.0, 1.0, 1.0),
            (0.0, 1.0, 1.0),
        ],
        dtype=float,
    )
    cells = np.asarray([8, 0, 1, 2, 3, 4, 5, 6, 7], dtype=np.int64)
    grid = pv.UnstructuredGrid(
        cells,
        np.asarray([pv.CellType.HEXAHEDRON], dtype=np.uint8),
        points,
    )
    grid.point_data["Stress"] = points[:, 0].copy()
    return grid


def test_section_cut_surface_fills_volume_and_interpolates_contour_values():
    cut = section_cut_surface(_hexahedron(), (0.5, 0.5, 0.5), (1.0, 0.0, 0.0))

    assert cut is not None
    assert cut.n_cells >= 1
    assert cut.n_points >= 4
    assert np.allclose(np.asarray(cut.points)[:, 0], 0.5)
    assert "Stress" in cut.point_data
    assert np.allclose(np.asarray(cut.point_data["Stress"]), 0.5)


def test_section_cut_surface_does_not_invent_a_cap_for_shells():
    points = np.asarray(
        [
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (1.0, 1.0, 0.0),
            (0.0, 1.0, 0.0),
        ],
        dtype=float,
    )
    shell = pv.UnstructuredGrid(
        np.asarray([4, 0, 1, 2, 3], dtype=np.int64),
        np.asarray([pv.CellType.QUAD], dtype=np.uint8),
        points,
    )

    assert section_cut_surface(shell, (0.5, 0.5, 0.0), (1.0, 0.0, 0.0)) is None
