"""Element-specific GPU interpolation for solver-result rendering.

Each supported legacy VTK finite-element type maps to one CellGrid HGRAD
interpolation specification. VTK turns every specification into a dedicated
OpenGL shader program; quadratic cells therefore evaluate their FE shape
functions in the tessellation shader instead of being CPU-linearized.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
import os
import tempfile

import numpy as np

_REGISTERED = False


@dataclass(frozen=True)
class ElementShaderSpec:
    vtk_cell_type: int
    name: str
    dg_type: str
    shape: str
    dimension: int
    corner_count: int
    node_count: int
    basis: str
    order: int
    # Local permutation from the legacy VTK/solver connectivity into the
    # ordering expected by the CellGrid basis. Empty means identity.
    basis_order: tuple[int, ...] = ()


_HEX20_BASIS_ORDER = (
    0, 1, 2, 3, 4, 5, 6, 7,
    8, 9, 10, 11,
    16, 17, 18, 19,
    12, 13, 14, 15,
)

_WEDGE15_BASIS_ORDER = (
    0, 1, 2, 3, 4, 5,
    6, 7, 8,
    12, 13, 14,
    9, 10, 11,
)


ELEMENT_SHADERS = {
    3: ElementShaderSpec(3, "LINE2", "vtkDGEdge", "edge", 1, 2, 2, "C", 1),
    21: ElementShaderSpec(21, "LINE3", "vtkDGEdge", "edge", 1, 2, 3, "C", 2),
    5: ElementShaderSpec(5, "TRI3", "vtkDGTri", "triangle", 2, 3, 3, "C", 1),
    22: ElementShaderSpec(22, "TRI6", "vtkDGTri", "triangle", 2, 3, 6, "C", 2),
    9: ElementShaderSpec(9, "QUAD4", "vtkDGQuad", "quadrilateral", 2, 4, 4, "C", 1),
    23: ElementShaderSpec(23, "QUAD8", "vtkDGQuad", "quadrilateral", 2, 4, 8, "I", 2),
    28: ElementShaderSpec(28, "QUAD9", "vtkDGQuad", "quadrilateral", 2, 4, 9, "C", 2),
    10: ElementShaderSpec(10, "TET4", "vtkDGTet", "tetrahedron", 3, 4, 4, "C", 1),
    24: ElementShaderSpec(24, "TET10", "vtkDGTet", "tetrahedron", 3, 4, 10, "C", 2),
    12: ElementShaderSpec(12, "HEX8", "vtkDGHex", "hexahedron", 3, 8, 8, "C", 1),
    25: ElementShaderSpec(
        25, "HEX20", "vtkDGHex", "hexahedron", 3, 8, 20, "I", 2,
        _HEX20_BASIS_ORDER,
    ),
    29: ElementShaderSpec(29, "HEX27", "vtkDGHex", "hexahedron", 3, 8, 27, "C", 2),
    13: ElementShaderSpec(13, "WEDGE6", "vtkDGWdg", "wedge", 3, 6, 6, "C", 1),
    26: ElementShaderSpec(
        26, "WEDGE15", "vtkDGWdg", "wedge", 3, 6, 15, "I", 2,
        _WEDGE15_BASIS_ORDER,
    ),
    32: ElementShaderSpec(32, "WEDGE18", "vtkDGWdg", "wedge", 3, 6, 18, "C", 2),
    14: ElementShaderSpec(14, "PYRAMID5", "vtkDGPyr", "pyramid", 3, 5, 5, "C", 1),
    27: ElementShaderSpec(27, "PYRAMID13", "vtkDGPyr", "pyramid", 3, 5, 13, "I", 2),
}


@dataclass
class _ShaderBatch:
    source: object
    surface: object
    specs: tuple[ElementShaderSpec, ...]
    cell_indices: dict[int, np.ndarray]
    connectivity: dict[int, np.ndarray]


class ElementShaderState:
    """Own immutable topology plus mutable coordinate/result GPU arrays."""

    def __init__(self, dataset, batches, scalar_name, association):
        self.dataset = dataset
        self.batches = tuple(batches)
        self.scalar_name = scalar_name
        self.association = association
        self._topology = None

    def remember_topology(self, grid):
        self._topology = (
            int(grid.GetNumberOfPoints()),
            int(grid.GetNumberOfCells()),
            _cell_types(grid).copy(),
        )

    def topology_matches(self, grid) -> bool:
        if self._topology is None:
            return False
        n_points, n_cells, types = self._topology
        return (
            n_points == int(grid.GetNumberOfPoints())
            and n_cells == int(grid.GetNumberOfCells())
            and np.array_equal(types, _cell_types(grid))
        )

    def update_values(self, grid, scalar_name=None) -> bool:
        scalar_name = self.scalar_name if scalar_name is None else scalar_name
        if (
            scalar_name != self.scalar_name
            or _scalar_association(grid, scalar_name) != self.association
        ):
            return False
        if not self.topology_matches(grid):
            return False

        from vtkmodules.util.numpy_support import vtk_to_numpy

        points = vtk_to_numpy(grid.GetPoints().GetData())
        point_values = None
        cell_values = None
        if scalar_name and self.association == "point":
            point_values = vtk_to_numpy(grid.GetPointData().GetArray(scalar_name))
        elif scalar_name and self.association == "cell":
            cell_values = vtk_to_numpy(grid.GetCellData().GetArray(scalar_name))

        for batch in self.batches:
            _overwrite_array(_group(batch.source, "points"), "coords", points, 3)
            if point_values is not None:
                _overwrite_array(_group(batch.source, "points"), scalar_name, point_values, 1)
            elif cell_values is not None:
                for spec in batch.specs:
                    values = cell_values[batch.cell_indices[spec.vtk_cell_type]]
                    _overwrite_array(_group(batch.source, spec.dg_type), scalar_name, values, 1)
            batch.source.Modified()
            batch.surface.Modified()
        self.dataset.Modified()
        return True


def install_element_shader_mapper(actor, grid, scalar_name=None, clim=None):
    """Replace an actor's legacy dataset mapper with the FE CellGrid GPU mapper.

    The actor and its PyVista-created property/scalar bar remain unchanged. This
    makes the shader path a rendering-only substitution; all higher-level result
    state continues to use the canonical UnstructuredGrid.
    """
    state = build_element_shader_state(grid, scalar_name)
    if state is None:
        return None
    try:
        legacy = actor.GetMapper()
    except (AttributeError, RuntimeError):
        return None
    mapper = _new_mapper(state, legacy, scalar_name, clim)
    if mapper is None:
        return None
    actor.SetMapper(mapper)
    actor._opencae_element_shader_state = state
    return mapper


def is_element_shader_actor(actor) -> bool:
    return getattr(actor, "_opencae_element_shader_state", None) is not None


def update_element_shader_mapper(actor, grid, scalar_name=None, clim=None):
    """Update coordinates/results in-place, rebuilding only when schema changes."""
    state = getattr(actor, "_opencae_element_shader_state", None)
    if state is None:
        return None
    mapper = actor.GetMapper()
    if not state.update_values(grid, scalar_name):
        replacement = build_element_shader_state(grid, scalar_name)
        if replacement is None:
            return None
        mapper.SetInputDataObject(replacement.dataset)
        actor._opencae_element_shader_state = replacement
    _configure_scalar_mapper(mapper, scalar_name, clim)
    mapper.Modified()
    return mapper


def _new_mapper(state, legacy_mapper, scalar_name, clim):
    _register_cellgrid()
    from vtkmodules.vtkRenderingCore import vtkCompositeCellGridMapper

    mapper = vtkCompositeCellGridMapper()
    mapper.SetInputDataObject(state.dataset)
    try:
        lookup = legacy_mapper.GetLookupTable()
        if lookup is not None:
            mapper.SetLookupTable(lookup)
        mapper.SetUseLookupTableScalarRange(legacy_mapper.GetUseLookupTableScalarRange())
        mapper.SetScalarRange(*legacy_mapper.GetScalarRange())
    except (AttributeError, RuntimeError, TypeError, ValueError):
        pass
    _configure_scalar_mapper(mapper, scalar_name, clim)
    return mapper


def _configure_scalar_mapper(mapper, scalar_name, clim):
    if not scalar_name:
        mapper.ScalarVisibilityOff()
        return
    mapper.ScalarVisibilityOn()
    # A CellGrid field is a cell attribute even when its HGRAD degrees of
    # freedom are shared nodal values. The responder evaluates that attribute
    # with the element-specific basis inside the GPU shader.
    mapper.SetScalarModeToUseCellFieldData()
    mapper.SetArrayName(str(scalar_name))
    mapper.SetArrayComponent(0)
    if clim is not None:
        scalar_range = tuple(float(value) for value in clim)
        mapper.SetScalarRange(*scalar_range)
        lookup = mapper.GetLookupTable()
        if lookup is not None:
            lookup.SetRange(*scalar_range)
            lookup.Modified()


def build_element_shader_state(grid, scalar_name=None):
    """Build batched element shaders for one fixed-topology result grid.

    Returns None when any cell type is unsupported so callers can fall back
    to the existing VTK dataset mapper without changing result semantics.
    """
    _register_cellgrid()
    if (
        grid is None
        or grid.GetNumberOfCells() <= 0
        or grid.GetNumberOfPoints() <= 0
    ):
        return None
    cell_types = _cell_types(grid)
    unique = tuple(int(value) for value in np.unique(cell_types))
    if any(cell_type not in ELEMENT_SHADERS for cell_type in unique):
        return None
    specs = tuple(ELEMENT_SHADERS[cell_type] for cell_type in unique)
    association = _scalar_association(grid, scalar_name)
    if scalar_name and association is None:
        return None

    partitions = _partition_specs(specs)
    batches = [
        _build_batch(grid, cell_types, group, scalar_name, association)
        for group in partitions
    ]
    if any(batch is None for batch in batches):
        return None

    # CellGrid removes shared faces inside each partition. Remove the remaining
    # duplicates between partitions (e.g. a HEX8 next to a HEX20) as well.
    _remove_cross_partition_internal_faces(batches)

    from vtkmodules.vtkCommonDataModel import vtkPartitionedDataSetCollection

    dataset = vtkPartitionedDataSetCollection()
    dataset.SetNumberOfPartitionedDataSets(len(batches))
    for index, batch in enumerate(batches):
        dataset.GetPartitionedDataSet(index).SetPartition(0, batch.surface)
    state = ElementShaderState(dataset, batches, scalar_name, association)
    state.remember_topology(grid)
    return state


def _partition_specs(specs):
    """Keep at most one interpolation order for each DG topology per CellGrid."""
    partitions: list[list[ElementShaderSpec]] = []
    for spec in specs:
        for partition in partitions:
            if all(item.dg_type != spec.dg_type for item in partition):
                partition.append(spec)
                break
        else:
            partitions.append([spec])
    return tuple(tuple(partition) for partition in partitions)


def _build_batch(grid, cell_types, specs, scalar_name, association):
    from vtkmodules.vtkCommonDataModel import vtkCellGrid
    from vtkmodules.util.numpy_support import vtk_to_numpy

    template = _template(
        tuple(spec.vtk_cell_type for spec in specs),
        scalar_name or "",
        association or "",
    )
    source = vtkCellGrid()
    source.DeepCopy(template)
    points = vtk_to_numpy(grid.GetPoints().GetData())
    point_group = _group(source, "points")
    _overwrite_array(point_group, "coords", points, 3)
    point_group.SetVectors(point_group.GetArray("coords"))
    if scalar_name and association == "point":
        values = vtk_to_numpy(grid.GetPointData().GetArray(scalar_name))
        _overwrite_array(_group(source, "points"), scalar_name, values, 1)

    offsets, connectivity = _connectivity(grid)
    cell_indices = {}
    batch_connectivity = {}
    cell_values = (
        vtk_to_numpy(grid.GetCellData().GetArray(scalar_name))
        if scalar_name and association == "cell"
        else None
    )
    for spec in specs:
        indices = np.flatnonzero(cell_types == spec.vtk_cell_type).astype(
            np.int64,
            copy=False,
        )
        counts = offsets[indices + 1] - offsets[indices]
        if len(counts) and not np.all(counts == spec.node_count):
            return None
        ids = connectivity[
            offsets[indices, None] + np.arange(spec.node_count, dtype=np.int64)
        ]
        cell_indices[spec.vtk_cell_type] = indices
        batch_connectivity[spec.vtk_cell_type] = ids
        # CellGrid expects the DG cell connectivity itself in basis order.
        # This mirrors vtkUnstructuredGridToCellGrid exactly: for HEX20 the
        # single 20-wide conn array is both the cell source and the HGRAD
        # connectivity. Using a separate 8-corner source breaks higher-order
        # side/face extraction.
        basis_ids = (
            ids[:, np.asarray(spec.basis_order, dtype=np.int64)]
            if spec.basis_order
            else ids
        )
        cell_group = _group(source, spec.dg_type)
        _overwrite_array(
            cell_group,
            "cell-connectivity",
            basis_ids,
            spec.node_count,
        )
        # vtkDGCell's canonical cell source is the group's active scalar array.
        # DeepCopy does not reliably preserve the active-array association across
        # VTK versions, so bind it explicitly just like the official transcriber.
        cell_group.SetScalars(cell_group.GetArray("cell-connectivity"))
        if cell_values is not None:
            _overwrite_array(
                _group(source, spec.dg_type),
                scalar_name,
                cell_values[indices],
                1,
            )
    source.Modified()
    surface = _surface_cellgrid(source)
    return _ShaderBatch(
        source,
        surface,
        tuple(specs),
        cell_indices,
        batch_connectivity,
    )


def _surface_cellgrid(source):
    from vtkmodules.vtkCommonDataModel import vtkCellGrid, vtkCellGridSidesQuery
    from vtkmodules.vtkFiltersCellGrid import vtkCellGridComputeSides

    sides = vtkCellGridComputeSides()
    sides.SetInputDataObject(source)
    sides.PreserveRenderableInputsOn()
    sides.OmitSidesForRenderableInputsOn()
    sides.SetOutputDimensionControl(vtkCellGridSidesQuery.SurfacesOfInputs)
    sides.Update()
    output = vtkCellGrid()
    # Keep the coordinate/result arrays shared with source so animation can
    # update them without regenerating side topology.
    output.ShallowCopy(sides.GetOutput())
    return output


def _remove_cross_partition_internal_faces(batches):
    if len(batches) < 2:
        return
    candidates = []
    for batch_index, batch in enumerate(batches):
        for spec in batch.specs:
            if spec.dimension != 3:
                continue
            metadata = _metadata(batch.surface, spec.dg_type)
            source_ids = batch.connectivity[spec.vtk_cell_type][
                :, : spec.corner_count
            ]
            for source_index in range(metadata.GetNumberOfCellSources()):
                side_source = metadata.GetCellSourceConnectivity(source_index)
                if side_source is None or side_source.GetNumberOfTuples() == 0:
                    continue
                from vtkmodules.util.numpy_support import vtk_to_numpy

                rows = vtk_to_numpy(side_source).reshape(
                    -1,
                    side_source.GetNumberOfComponents(),
                )
                if rows.shape[1] < 2:
                    continue
                for row_index, (parent, side_id, *_rest) in enumerate(rows):
                    local = metadata.GetSideConnectivity(int(side_id))
                    key = tuple(
                        sorted(
                            int(source_ids[int(parent), int(node)])
                            for node in local
                        )
                    )
                    candidates.append(
                        (
                            key,
                            batch_index,
                            spec.dg_type,
                            source_index,
                            row_index,
                        )
                    )
    if not candidates:
        return

    counts = {}
    for key, *_ in candidates:
        counts[key] = counts.get(key, 0) + 1
    removals = {}
    for key, batch_index, dg_type, source_index, row_index in candidates:
        if counts[key] > 1:
            removals.setdefault(
                (batch_index, dg_type, source_index),
                set(),
            ).add(row_index)
    if not removals:
        return

    from vtkmodules.util.numpy_support import vtk_to_numpy

    for (batch_index, dg_type, source_index), remove in removals.items():
        surface = batches[batch_index].surface
        metadata = _metadata(surface, dg_type)
        target = metadata.GetCellSourceConnectivity(source_index)
        rows = vtk_to_numpy(target).reshape(
            -1,
            target.GetNumberOfComponents(),
        )
        keep = np.ones(len(rows), dtype=bool)
        keep[list(remove)] = False
        _overwrite_vtk_array(
            target,
            rows[keep],
            target.GetNumberOfComponents(),
        )
        metadata.Modified()
        surface.Modified()


def _metadata(cellgrid, dg_type):
    from vtkmodules.vtkCommonCore import vtkStringToken

    return cellgrid.GetCellType(vtkStringToken(dg_type))


def _cell_types(grid):
    from vtkmodules.util.numpy_support import vtk_to_numpy

    return vtk_to_numpy(grid.GetCellTypesArray()).astype(np.int64, copy=False)


def _connectivity(grid):
    from vtkmodules.util.numpy_support import vtk_to_numpy

    cells = grid.GetCells()
    offsets = vtk_to_numpy(cells.GetOffsetsArray()).astype(np.int64, copy=False)
    connectivity = vtk_to_numpy(cells.GetConnectivityArray()).astype(
        np.int64,
        copy=False,
    )
    return offsets, connectivity


def _scalar_association(grid, scalar_name):
    if not scalar_name:
        return None
    if grid.GetPointData().HasArray(str(scalar_name)):
        return "point"
    if grid.GetCellData().HasArray(str(scalar_name)):
        return "cell"
    return None


def _group(cellgrid, name):
    from vtkmodules.vtkCommonCore import vtkStringToken

    return cellgrid.GetAttributes(vtkStringToken(name))


def _overwrite_array(group, name, values, components):
    target = group.GetArray(str(name))
    if target is None:
        raise KeyError(f"CellGrid array {name!r} is missing")
    _overwrite_vtk_array(target, values, components)
    target.SetName(str(name))


def _overwrite_vtk_array(target, values, components):
    from vtkmodules.util.numpy_support import numpy_to_vtk

    array = np.asarray(values).reshape(-1, components)
    source = numpy_to_vtk(
        np.ascontiguousarray(array),
        deep=True,
        array_type=target.GetDataType(),
    )
    source.SetNumberOfComponents(int(components))
    target.DeepCopy(source)
    target.Modified()


def _register_cellgrid():
    global _REGISTERED
    if _REGISTERED:
        return
    from vtkmodules.vtkFiltersCellGrid import vtkFiltersCellGrid
    from vtkmodules.vtkRenderingCellGrid import vtkRenderingCellGrid

    vtkFiltersCellGrid.RegisterCellsAndResponders()
    vtkRenderingCellGrid.RegisterCellsAndResponders()
    _REGISTERED = True


@lru_cache(maxsize=64)
def _template(cell_types, scalar_name, association):
    specs = tuple(ELEMENT_SHADERS[int(cell_type)] for cell_type in cell_types)
    document = _template_document(
        specs,
        scalar_name or None,
        association or None,
    )
    payload = json.dumps(
        document,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    from vtkmodules.vtkCommonDataModel import vtkCellGrid
    from vtkmodules.vtkIOCellGrid import vtkCellGridReader

    descriptor, path = tempfile.mkstemp(
        prefix="opencae-cellgrid-",
        suffix=".dg",
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(payload)
        reader = vtkCellGridReader()
        reader.SetFileName(path)
        reader.Update()
        template = vtkCellGrid()
        template.DeepCopy(reader.GetOutput())
        if template.GetNumberOfCells() != len(specs):
            raise RuntimeError(
                "VTK rejected the OpenCAE element-shader description"
            )
        return template
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _template_document(specs, scalar_name, association):
    point_arrays = [
        {
            "components": 3,
            "data": [0.0, 0.0, 0.0],
            "default_scalars": True,
            "name": "coords",
            "tuples": 1,
            "type": "double",
        }
    ]
    if scalar_name and association == "point":
        point_arrays.append(
            {
                "components": 1,
                "data": [0.0],
                "name": scalar_name,
                "tuples": 1,
                "type": "double",
            }
        )
    arrays = {"points": point_arrays}
    shape_info = {}
    scalar_info = {}
    cell_types = []
    for spec in specs:
        type_arrays = [
            {
                "components": spec.node_count,
                "data": list(range(spec.node_count)),
                "default_scalars": True,
                "name": "cell-connectivity",
                "tuples": 1,
                "type": "vtktypeint64",
            },
        ]
        if scalar_name and association == "cell":
            type_arrays.append(
                {
                    "components": 1,
                    "data": [0.0],
                    "name": scalar_name,
                    "tuples": 1,
                    "type": "double",
                }
            )
        arrays[spec.dg_type] = type_arrays
        shape_info[spec.dg_type] = _hgrad_info(spec, "coords")
        if scalar_name:
            scalar_info[spec.dg_type] = (
                _hgrad_info(spec, scalar_name)
                if association == "point"
                else {
                    "arrays": {
                        "connectivity": [
                            spec.dg_type,
                            "cell-connectivity",
                        ],
                        "values": [spec.dg_type, scalar_name],
                    },
                    "basis": "C",
                    "function-space": "constant",
                    "order": 0,
                }
            )
        cell_types.append(
            {
                "cell-spec": {
                    "connectivity": [
                        spec.dg_type,
                        "cell-connectivity",
                    ],
                    "shape": spec.shape,
                },
                "type": spec.dg_type,
            }
        )
    attributes = [
        {
            "cell-info": shape_info,
            "components": 3,
            "name": "shape",
            "shape": True,
            "space": "ℝ³",
        }
    ]
    if scalar_name:
        attributes.append(
            {
                "cell-info": scalar_info,
                "components": 1,
                "name": scalar_name,
                "space": "ℝ",
            }
        )
    return {
        "arrays": arrays,
        "attributes": attributes,
        "cell-types": cell_types,
        "content-version": 0,
        "data-type": "cell-grid",
        "format-version": 1,
        "schema-name": "dg leaf",
        "schema-version": 0,
    }


def _hgrad_info(spec, value_name):
    return {
        "arrays": {
            "connectivity": [spec.dg_type, "cell-connectivity"],
            "values": ["points", value_name],
        },
        "basis": spec.basis,
        "dof-sharing": "CG",
        "function-space": "HGRAD",
        "order": spec.order,
    }
