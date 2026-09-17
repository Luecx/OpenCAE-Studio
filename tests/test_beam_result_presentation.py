"""Regression coverage for the canonical FRD beam result presentation."""

from __future__ import annotations

import numpy as np
import pyvista as pv

from opencae.results.beam_physical_representation import (
    BEAM_CENTERLINE_CELL,
    PHYSICAL_BEAM_CELL,
)
from opencae.results.beam_physical_stress import stress_display_values
from opencae.ui.other.viewport.result_visualization import _beam_subset, _mesh_edge_grid
from opencae.ui.other.viewport.scalar_bar import update_scalar_bar_title
from opencae.ui.other.viewport.section_view import section_cut_surface


def _superset_grid():
    points = np.asarray(
        (
            (-0.5, 0.5, 0.5),
            (1.5, 0.5, 0.5),
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
    cells = np.asarray(
        (2, 0, 1, 8, 2, 3, 4, 5, 6, 7, 8, 9),
        dtype=np.int64,
    )
    grid = pv.UnstructuredGrid(
        cells,
        np.asarray((pv.CellType.LINE, pv.CellType.HEXAHEDRON), dtype=np.uint8),
        points,
    )
    grid.cell_data[BEAM_CENTERLINE_CELL] = np.asarray((1, 0), dtype=np.uint8)
    grid.cell_data[PHYSICAL_BEAM_CELL] = np.asarray((0, 1), dtype=np.uint8)
    grid.cell_data["element_id"] = np.asarray((7, 7), dtype=np.int64)
    return grid


def test_beam_button_filters_one_canonical_superset_instead_of_rebuilding_geometry():
    grid = _superset_grid()

    line_view = _beam_subset(grid, False)
    physical_view = _beam_subset(grid, True)

    assert line_view.n_cells == 1
    assert int(line_view.celltypes[0]) == int(pv.CellType.LINE)
    assert physical_view.n_cells == 1
    assert int(physical_view.celltypes[0]) == int(pv.CellType.HEXAHEDRON)
    np.testing.assert_array_equal(line_view.cell_data["element_id"], (7,))
    np.testing.assert_array_equal(physical_view.cell_data["element_id"], (7,))


def test_undeformed_edges_exist_for_both_line_and_physical_beam_subsets():
    grid = _superset_grid()

    line_edges = _mesh_edge_grid(_beam_subset(grid, False))
    physical_edges = _mesh_edge_grid(_beam_subset(grid, True))

    assert line_edges.n_cells > 0
    assert physical_edges.n_cells > 0


def test_section_cut_produces_a_filled_face_for_physical_beam_hexes():
    physical = _beam_subset(_superset_grid(), True)

    cut = section_cut_surface(
        physical,
        origin=(0.5, 0.5, 0.5),
        normal=(1.0, 0.0, 0.0),
    )

    assert cut is not None
    assert cut.n_cells > 0
    assert cut.n_points >= 4


def test_recovered_beam_stress_maps_only_to_sxx_tensor_component():
    values = np.asarray((-12.0, 8.0), dtype=float)

    np.testing.assert_allclose(stress_display_values("STRESS:SXX", values), values)
    for component in ("SYY", "SZZ", "SXY", "SYZ", "SZX"):
        np.testing.assert_allclose(
            stress_display_values(f"STRESS:{component}", values),
            0.0,
        )
    np.testing.assert_allclose(
        stress_display_values("STRESS:Mises", values),
        np.abs(values),
    )
    np.testing.assert_allclose(
        stress_display_values("STRESS:Magnitude", values),
        np.abs(values),
    )


class _ScalarActor:
    def __init__(self):
        self.title = ""
        self.modified = False

    def SetTitle(self, value):
        self.title = str(value)

    def Modified(self):
        self.modified = True


class _ScalarPlotter:
    def __init__(self):
        self.scalar_bar = _ScalarActor()
        self.scalar_bars = {}


def test_scalar_bar_title_tracks_the_active_result_component():
    plotter = _ScalarPlotter()

    update_scalar_bar_title(plotter, "DISP:Magnitude")
    assert plotter.scalar_bar.title == "DISP — Magnitude"

    update_scalar_bar_title(plotter, "STRESS:SXX")
    assert plotter.scalar_bar.title == "STRESS — SXX"
    assert plotter.scalar_bar.modified
