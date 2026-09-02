import numpy as np
import pyvista as pv

from opencae.ui.viewport.section_view import SectionViewController, section_cut_surface


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


def test_moved_section_keeps_selected_point_scalar_in_pyvista_mapper_pipeline():
    grid = _hexahedron()
    grid.point_data["Decoy"] = 100.0 + np.asarray(grid.points)[:, 0]
    grid.set_active_scalars("Decoy", preference="point")

    first_cut = section_cut_surface(grid, (0.1, 0.5, 0.5), (1.0, 0.0, 0.0))
    assert first_cut is not None
    mapper = pv.DataSetMapper(dataset=first_cut)
    mapper.set_active_scalars("Stress", preference="point")
    mapper.scalar_range = (0.0, 1.0)

    for x in (0.25, 0.75, 0.4):
        moved_cut = section_cut_surface(grid, (x, 0.5, 0.5), (1.0, 0.0, 0.0))
        assert moved_cut is not None
        assert moved_cut.active_scalars_name == "Decoy"

        assert SectionViewController._bind_cap_dataset(mapper, moved_cut, "Stress")
        mapper.update()
        mapped = pv.wrap(mapper.GetInput())

        assert mapper.scalar_map_mode == "point"
        assert mapper.array_name == "Stress"
        assert mapped.active_scalars_name == "Stress"
        assert np.allclose(np.asarray(mapped.active_scalars), x)


def test_moved_section_rebinds_cell_scalar_association():
    grid = _hexahedron()
    grid.cell_data["ElementValue"] = np.asarray([7.5])
    cut = section_cut_surface(grid, (0.5, 0.5, 0.5), (1.0, 0.0, 0.0))

    assert cut is not None
    mapper = pv.DataSetMapper(dataset=cut)
    assert SectionViewController._bind_cap_dataset(mapper, cut, "ElementValue")
    mapper.update()

    assert mapper.scalar_map_mode == "cell"
    assert mapper.array_name == "ElementValue"
    assert np.allclose(np.asarray(mapper._mapped_scalars), 7.5)


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
