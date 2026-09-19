import numpy as np
from vtkmodules.util.numpy_support import numpy_to_vtk, vtk_to_numpy
from vtkmodules.vtkCommonCore import vtkIdList, vtkLookupTable, vtkPoints
from vtkmodules.vtkCommonDataModel import vtkUnstructuredGrid
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkCompositeCellGridMapper,
    vtkDataSetMapper,
)

from opencae.ui.viewport import element_shader_rendering as shaders
from opencae.ui.viewport import result_visualization as result_view


def _grid(cells, point_count, scalar="S"):
    grid = vtkUnstructuredGrid()
    points = vtkPoints()
    coordinates = (
        np.arange(point_count * 3, dtype=float).reshape(point_count, 3) / 11.0
    )
    points.SetData(numpy_to_vtk(coordinates, deep=True))
    grid.SetPoints(points)
    for cell_type, ids in cells:
        vtk_ids = vtkIdList()
        for value in ids:
            vtk_ids.InsertNextId(int(value))
        grid.InsertNextCell(int(cell_type), vtk_ids)
    if scalar:
        values = numpy_to_vtk(
            np.linspace(-1.0, 1.0, point_count),
            deep=True,
        )
        values.SetName(scalar)
        grid.GetPointData().AddArray(values)
    return grid


def _side_count(batch, spec):
    metadata = shaders._metadata(batch.surface, spec.dg_type)
    return sum(
        metadata.GetCellSourceConnectivity(index).GetNumberOfTuples()
        for index in range(metadata.GetNumberOfCellSources())
    )


def test_current_frd_cell_families_have_element_shader_specs():
    expected = {3, 5, 9, 10, 12, 13, 21, 22, 23, 24, 25, 26}
    assert expected <= set(shaders.ELEMENT_SHADERS)
    assert shaders.ELEMENT_SHADERS[25].name == "HEX20"
    assert shaders.ELEMENT_SHADERS[25].basis == "I"
    assert shaders.ELEMENT_SHADERS[25].order == 2
    assert shaders.ELEMENT_SHADERS[24].basis == "C"
    assert shaders.ELEMENT_SHADERS[24].order == 2


def test_hex20_builds_quadratic_hgrad_shader_surface():
    grid = _grid([(25, range(20))], 20)
    state = shaders.build_element_shader_state(grid, "S")

    assert state is not None
    assert len(state.batches) == 1
    batch = state.batches[0]
    assert [item.name for item in batch.specs] == ["HEX20"]
    assert _side_count(batch, batch.specs[0]) == 6

    document = shaders._template_document(batch.specs, "S", "point")
    shape = document["attributes"][0]["cell-info"]["vtkDGHex"]
    scalar = document["attributes"][1]["cell-info"]["vtkDGHex"]
    assert (shape["dof-sharing"], shape["function-space"], shape["basis"], shape["order"]) == (
        "CG",
        "HGRAD",
        "I",
        2,
    )
    assert (scalar["dof-sharing"], scalar["function-space"], scalar["basis"], scalar["order"]) == (
        "CG",
        "HGRAD",
        "I",
        2,
    )
    assert shaders._group(batch.source, "vtkDGHex").GetScalars() is not None
    assert shaders._group(batch.source, "vtkDGHex").GetScalars().GetNumberOfComponents() == 20



def test_hex20_reorders_vtk_connectivity_for_cellgrid_i2_basis():
    grid = _grid([(25, range(20))], 20)
    state = shaders.build_element_shader_state(grid, "S")

    batch = state.batches[0]
    connectivity = vtk_to_numpy(
        shaders._group(batch.source, "vtkDGHex").GetArray("cell-connectivity")
    ).reshape(-1, 20)
    assert connectivity.tolist() == [[
        0, 1, 2, 3, 4, 5, 6, 7,
        8, 9, 10, 11,
        16, 17, 18, 19,
        12, 13, 14, 15,
    ]]


def test_wedge15_reorders_top_and_vertical_mid_edge_nodes_for_i2_basis():
    grid = _grid([(26, range(15))], 15)
    state = shaders.build_element_shader_state(grid, "S")

    batch = state.batches[0]
    connectivity = vtk_to_numpy(
        shaders._group(batch.source, "vtkDGWdg").GetArray("cell-connectivity")
    ).reshape(-1, 15)
    assert connectivity.tolist() == [[
        0, 1, 2, 3, 4, 5,
        6, 7, 8,
        12, 13, 14,
        9, 10, 11,
    ]]


def test_frd_hex20_normalizes_to_vtk_then_cellgrid_basis():
    import pyvista as pv
    from vtkmodules.vtkFiltersCellGrid import vtkUnstructuredGridToCellGrid

    # FEMaster's FRD writer emits CalculiX/CGX type-4 connectivity in this
    # order, while the declared VTK_QUADRATIC_HEXAHEDRON cell expects 0..19.
    frd_order = [
        0, 1, 2, 3, 4, 5, 6, 7,
        8, 9, 10, 11,
        16, 17, 18, 19,
        12, 13, 14, 15,
    ]
    frd_grid = pv.wrap(_grid([(25, frd_order)], 20))
    vtk_grid = result_view._vtk_ordered_frd_grid(frd_grid)

    offsets = vtk_to_numpy(vtk_grid.GetCells().GetOffsetsArray())
    ids = vtk_to_numpy(vtk_grid.GetCells().GetConnectivityArray())
    local = ids[int(offsets[0]):int(offsets[1])]
    assert local.tolist() == list(range(20))

    ours = shaders.build_element_shader_state(vtk_grid, "S")
    ours_conn = vtk_to_numpy(
        shaders._group(ours.batches[0].source, "vtkDGHex").GetScalars()
    ).reshape(-1, 20)

    converter = vtkUnstructuredGridToCellGrid()
    converter.SetInputDataObject(0, vtk_grid)
    converter.Update()
    pdc = converter.GetOutputDataObject(0)
    official = pdc.GetPartitionedDataSet(0).GetPartitionAsDataObject(0)
    expected_basis_order = [[
        0, 1, 2, 3, 4, 5, 6, 7,
        8, 9, 10, 11,
        16, 17, 18, 19,
        12, 13, 14, 15,
    ]]
    # This verifies our ordering independently of converter support. Some
    # packaged VTK versions report quadratic HEX as an unhandled input cell,
    # so their official converter cannot serve as a reference in those builds.
    assert ours_conn.tolist() == expected_basis_order
    official_array = official.GetAttributes("vtkDGHex").GetScalars()
    if official_array is not None:
        official_conn = vtk_to_numpy(official_array).reshape(-1, 20)
        assert ours_conn.tolist() == official_conn.tolist()


def test_frd_wedge15_normalizes_back_to_vtk_order():
    import pyvista as pv

    frd_order = [
        0, 1, 2, 3, 4, 5,
        6, 7, 8,
        12, 13, 14,
        9, 10, 11,
    ]
    frd_grid = pv.wrap(_grid([(26, frd_order)], 15))
    vtk_grid = result_view._vtk_ordered_frd_grid(frd_grid)

    offsets = vtk_to_numpy(vtk_grid.GetCells().GetOffsetsArray())
    ids = vtk_to_numpy(vtk_grid.GetCells().GetConnectivityArray())
    local = ids[int(offsets[0]):int(offsets[1])]
    assert local.tolist() == list(range(15))

def test_mixed_hex_orders_use_separate_shader_batches_and_remove_interface():
    # HEX8 top face [4,5,6,7] is HEX20 bottom face [4,5,6,7]. The different
    # interpolation orders require separate CellGrid batches, but the shared
    # material interface must not survive as two coincident render surfaces.
    hex8 = list(range(8))
    hex20 = [4, 5, 6, 7, 8, 9, 10, 11, *range(12, 24)]
    grid = _grid([(12, hex8), (25, hex20)], 24)

    state = shaders.build_element_shader_state(grid, "S")

    assert state is not None
    assert len(state.batches) == 2
    counts = {
        batch.specs[0].name: _side_count(batch, batch.specs[0])
        for batch in state.batches
    }
    assert counts == {"HEX8": 5, "HEX20": 5}


def _add_point_array(grid, name, values):
    array = numpy_to_vtk(np.asarray(values, dtype=float), deep=True)
    array.SetName(name)
    grid.GetPointData().AddArray(array)


def test_stress_magnitude_interpolates_six_components_before_l2_reduction():
    grid = _grid([(25, range(20))], 20, scalar=None)
    names = (
        "STRESS:SXX", "STRESS:SYY", "STRESS:SZZ",
        "STRESS:SXY", "STRESS:SYZ", "STRESS:SZX",
    )
    columns = []
    for index, name in enumerate(names):
        values = np.linspace(index + 1.0, index + 3.0, 20)
        columns.append(values)
        _add_point_array(grid, name, values)
    nodal_magnitude = np.linalg.norm(np.column_stack(columns), axis=1)
    _add_point_array(grid, "STRESS:Magnitude", nodal_magnitude)

    field = shaders.color_field(
        grid,
        "STRESS:Magnitude",
        names,
        magnitude=True,
    )
    state = shaders.build_element_shader_state(grid, field)

    assert field.components == 6
    values = vtk_to_numpy(
        shaders._group(state.batches[0].source, "points").GetArray("STRESS:Magnitude")
    ).reshape(-1, 6)
    np.testing.assert_allclose(values, np.column_stack(columns))


def test_mises_transform_norm_equals_mises_of_stress_tensor():
    grid = _grid([(25, range(20))], 20, scalar=None)
    names = (
        "STRESS:SXX", "STRESS:SYY", "STRESS:SZZ",
        "STRESS:SXY", "STRESS:SYZ", "STRESS:SZX",
    )
    raw = np.column_stack((
        np.linspace(100.0, 160.0, 20),
        np.linspace(20.0, 40.0, 20),
        np.linspace(-10.0, 15.0, 20),
        np.linspace(5.0, 9.0, 20),
        np.linspace(-3.0, 2.0, 20),
        np.linspace(7.0, 11.0, 20),
    ))
    for index, name in enumerate(names):
        _add_point_array(grid, name, raw[:, index])

    field = shaders.color_field(
        grid,
        "STRESS:Mises",
        names,
        transform="mises",
        magnitude=True,
    )
    transformed = shaders._color_values(grid, field)
    rendered = np.linalg.norm(transformed, axis=1)
    sxx, syy, szz, sxy, syz, szx = raw.T
    expected = np.sqrt(
        0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
        + 3.0 * (sxy ** 2 + syz ** 2 + szx ** 2)
    )
    np.testing.assert_allclose(rendered, expected)
    assert np.all(rendered >= 0.0)


def test_derived_color_mapper_uses_vector_magnitude_mode():
    grid = _grid([(25, range(20))], 20, scalar=None)
    names = ("DISP:D1", "DISP:D2", "DISP:D3")
    for index, name in enumerate(names):
        _add_point_array(grid, name, np.linspace(0.0, index + 1.0, 20))
    field = shaders.color_field(grid, "DISP:Magnitude", names, magnitude=True)

    legacy = vtkDataSetMapper()
    legacy.SetInputData(grid)
    lookup = vtkLookupTable()
    lookup.SetRange(0.0, 2.0)
    legacy.SetLookupTable(lookup)
    actor = vtkActor()
    actor.SetMapper(legacy)

    mapper = shaders.install_element_shader_mapper(actor, grid, field, (0.0, 2.0))

    assert mapper is not None
    assert mapper.GetArrayName() == "DISP:Magnitude"
    assert mapper.GetLookupTable().GetVectorMode() == 0


def test_result_field_selection_uses_raw_stress_components_for_magnitude():
    from types import SimpleNamespace

    grid = _grid([(25, range(20))], 20, scalar=None)
    names = (
        "STRESS:SXX", "STRESS:SYY", "STRESS:SZZ",
        "STRESS:SXY", "STRESS:SYZ", "STRESS:SZX",
    )
    for index, name in enumerate(names):
        _add_point_array(grid, name, np.full(20, float(index + 1)))
    _add_point_array(grid, "STRESS:Magnitude", np.ones(20))
    _add_point_array(grid, "_opencae_display_scalar", np.ones(20))
    field = SimpleNamespace(name="STRESS", metadata={"component": "Magnitude"})

    spec = result_view._shader_color_field(
        grid, field, "STRESS:Magnitude", "_opencae_display_scalar"
    )

    assert spec.name == "STRESS:Magnitude"
    assert spec.source_names == names
    assert spec.magnitude
    assert spec.transform == "identity"
    clim = result_view._clim(
        grid, "STRESS:Magnitude", {}, nonnegative=True
    )
    assert clim[0] >= 0.0

def test_mapper_swap_preserves_lookup_table_and_updates_gpu_arrays_in_place():
    grid = _grid([(25, range(20))], 20)
    legacy = vtkDataSetMapper()
    legacy.SetInputData(grid)
    lookup = vtkLookupTable()
    lookup.SetRange(-1.0, 1.0)
    legacy.SetLookupTable(lookup)
    legacy.SetScalarRange(-1.0, 1.0)
    actor = vtkActor()
    actor.SetMapper(legacy)

    mapper = shaders.install_element_shader_mapper(
        actor,
        grid,
        "S",
        (-2.0, 2.0),
    )

    assert isinstance(mapper, vtkCompositeCellGridMapper)
    assert actor.GetMapper() is mapper
    assert mapper.GetLookupTable() is lookup
    assert mapper.GetUseLookupTableScalarRange()
    assert mapper.GetArrayName() == "S"
    assert mapper.GetScalarRange() == (-2.0, 2.0)
    assert mapper.GetLookupTable().GetRange() == (-2.0, 2.0)

    points = vtk_to_numpy(grid.GetPoints().GetData())
    points[:, 0] += 7.0
    grid.GetPoints().GetData().Modified()
    values = vtk_to_numpy(grid.GetPointData().GetArray("S"))
    values[:] += 3.0
    grid.GetPointData().GetArray("S").Modified()

    updated = shaders.update_element_shader_mapper(
        actor,
        grid,
        "S",
        (-4.0, 4.0),
    )
    state = actor._opencae_element_shader_state
    batch = state.batches[0]
    gpu_points = vtk_to_numpy(
        shaders._group(batch.source, "points").GetArray("coords")
    )
    gpu_values = vtk_to_numpy(
        shaders._group(batch.source, "points").GetArray("S")
    )

    assert updated is mapper
    assert np.allclose(gpu_points.reshape(-1, 3), points)
    assert np.allclose(gpu_values.reshape(-1), values)
    assert mapper.GetUseLookupTableScalarRange()
    assert mapper.GetScalarRange() == (-4.0, 4.0)
    assert mapper.GetLookupTable().GetRange() == (-4.0, 4.0)


def test_unsupported_legacy_cell_falls_back_without_building_cellgrid():
    grid = _grid([(1, [0])], 1)
    assert shaders.build_element_shader_state(grid, "S") is None
