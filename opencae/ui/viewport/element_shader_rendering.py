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
class ColorFieldSpec:
    """Describe values CellGrid interpolates before color reduction.

    source_names identify scalar arrays on the canonical result grid. They
    are packed into one multi-component HGRAD attribute. transform is
    restricted to linear transforms so it commutes with FE interpolation.
    When magnitude is true, VTK reduces the interpolated tuple to its L2
    norm in the fragment shader.
    """

    name: str
    association: str
    source_names: tuple[str, ...]
    transform: str = "identity"
    magnitude: bool = False

    @property
    def components(self) -> int:
        if self.transform == "mises":
            return 6
        return len(self.source_names)

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


def color_field(
    grid,
    name,
    source_names=None,
    *,
    transform="identity",
    magnitude=False,
):
    """Return a validated render-field description or None.

    The common path accepts a single scalar name. Derived fields pass their raw
    component arrays instead, so CellGrid interpolates the components before
    taking a norm.
    """
    if not name:
        return None
    names = tuple(source_names or (str(name),))
    if not names:
        return None
    association = None
    for source in names:
        current = _scalar_association(grid, source)
        if current is None:
            return None
        if association is None:
            association = current
        elif current != association:
            return None
    field = ColorFieldSpec(
        str(name),
        str(association),
        tuple(str(source) for source in names),
        str(transform),
        bool(magnitude),
    )
    if field.components <= 0:
        return None
    return field


def _coerce_color_field(grid, value):
    if value is None:
        return None
    if isinstance(value, ColorFieldSpec):
        for source in value.source_names:
            if _scalar_association(grid, source) != value.association:
                return None
        return value
    return color_field(grid, str(value))


def _color_values(grid, field):
    if field is None:
        return None
    data = (
        grid.GetPointData()
        if field.association == "point"
        else grid.GetCellData()
    )
    from vtkmodules.util.numpy_support import vtk_to_numpy

    columns = []
    for source in field.source_names:
        array = data.GetArray(source)
        if array is None:
            return None
        values = np.asarray(vtk_to_numpy(array), dtype=float)
        if values.ndim != 1:
            values = values.reshape(values.shape[0], -1)
            if values.shape[1] != 1:
                return None
            values = values[:, 0]
        columns.append(values)
    packed = np.column_stack(columns)
    if field.transform == "identity":
        return packed
    if field.transform == "mises":
        if packed.shape[1] != 6:
            return None
        sxx, syy, szz, sxy, syz, szx = packed.T
        inv_sqrt2 = 1.0 / np.sqrt(2.0)
        sqrt3 = np.sqrt(3.0)
        return np.column_stack((
            (sxx - syy) * inv_sqrt2,
            (syy - szz) * inv_sqrt2,
            (szz - sxx) * inv_sqrt2,
            sqrt3 * sxy,
            sqrt3 * syz,
            sqrt3 * szx,
        ))
    return None


def _gpu_color_mapping(color, clim):
    """Return (offset, scale, GPU range) for one physical contour range.

    CellGrid evaluates field coefficients and color coordinates in GPU float
    precision. Normalize scalar coefficients before upload so its LUT sees
    well-scaled values, while the scalar bar keeps physical units.

    Direct scalar interpolation permits an affine transform. For a magnitude
    (including the linearly transformed von Mises tuple), ONLY use a common
    positive scale: subtracting an offset from the vector/tensor components
    before taking their norm would change the physical quantity.
    """
    if color is None or clim is None:
        return None
    lower, upper = (float(value) for value in clim)
    if not np.isfinite(lower) or not np.isfinite(upper) or upper <= lower:
        return None
    if color.magnitude:
        scale = max(abs(lower), abs(upper))
        if scale <= 0.0:
            return None
        return 0.0, scale, (lower / scale, upper / scale)
    if color.transform == "identity" and color.components == 1:
        return lower, upper - lower, (0.0, 1.0)
    return None


def _gpu_color_values(grid, color, clim):
    values = _color_values(grid, color)
    mapping = _gpu_color_mapping(color, clim)
    if values is None or mapping is None:
        return values
    offset, scale, _gpu_range = mapping
    # Never clip: preserve genuine values outside the colorbar limits.
    # Original result/query arrays remain untouched.
    return (values - offset) / scale


@dataclass
class _ShaderBatch:
    source: object
    surface: object
    specs: tuple[ElementShaderSpec, ...]
    cell_indices: dict[int, np.ndarray]
    connectivity: dict[int, np.ndarray]


class ElementShaderState:
    """Own immutable topology plus mutable coordinate/result GPU arrays."""

    def __init__(self, dataset, batches, color):
        self.dataset = dataset
        self.batches = tuple(batches)
        self.color = color
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

    def update_values(self, grid, color=None, clim=None) -> bool:
        color = self.color if color is None else _coerce_color_field(grid, color)
        if color != self.color or not self.topology_matches(grid):
            return False

        from vtkmodules.util.numpy_support import vtk_to_numpy

        points = vtk_to_numpy(grid.GetPoints().GetData())
        values = _gpu_color_values(grid, color, clim)
        if color is not None and values is None:
            return False

        for batch in self.batches:
            _overwrite_array(_group(batch.source, "points"), "coords", points, 3)
            if color is not None and color.association == "point":
                _overwrite_array(
                    _group(batch.source, "points"),
                    color.name,
                    values,
                    color.components,
                )
            elif color is not None and color.association == "cell":
                for spec in batch.specs:
                    selected = values[batch.cell_indices[spec.vtk_cell_type]]
                    _overwrite_array(
                        _group(batch.source, spec.dg_type),
                        color.name,
                        selected,
                        color.components,
                    )
            batch.source.Modified()
            batch.surface.Modified()
        self.dataset.Modified()
        return True


def install_element_shader_mapper(actor, grid, color=None, clim=None):
    """Replace an actor's legacy dataset mapper with the FE CellGrid GPU mapper."""
    color = _coerce_color_field(grid, color)
    state = build_element_shader_state(grid, color, clim)
    if state is None:
        return None
    try:
        legacy = actor.GetMapper()
    except (AttributeError, RuntimeError):
        return None
    mapper = _new_mapper(state, legacy, color, clim)
    if mapper is None:
        return None
    actor.SetMapper(mapper)
    actor._opencae_element_shader_state = state
    return mapper


def is_element_shader_actor(actor) -> bool:
    return getattr(actor, "_opencae_element_shader_state", None) is not None


def update_element_shader_mapper(actor, grid, color=None, clim=None):
    """Update coordinates/results in-place, rebuilding only when schema changes."""
    state = getattr(actor, "_opencae_element_shader_state", None)
    if state is None:
        return None
    color = _coerce_color_field(grid, color)
    mapper = actor.GetMapper()
    if not state.update_values(grid, color, clim):
        replacement = build_element_shader_state(grid, color, clim)
        if replacement is None:
            return None
        mapper.SetInputDataObject(replacement.dataset)
        actor._opencae_element_shader_state = replacement
        state = replacement
    _configure_scalar_mapper(mapper, state.color, clim)
    mapper.Modified()
    return mapper


def _new_mapper(state, legacy_mapper, color, clim):
    _register_cellgrid()
    from vtkmodules.vtkRenderingCore import vtkCompositeCellGridMapper

    mapper = vtkCompositeCellGridMapper()
    mapper.SetInputDataObject(state.dataset)
    try:
        lookup = legacy_mapper.GetLookupTable()
        if lookup is not None:
            mapping = _gpu_color_mapping(color, clim)
            if mapping is not None:
                # Keep the original LUT for the physical-unit scalar bar.
                # The GPU requires an independent copy with its mapped range.
                gpu_lookup = lookup.NewInstance()
                gpu_lookup.DeepCopy(lookup)
                gpu_lookup.SetRange(*mapping[2])
                mapper.SetLookupTable(gpu_lookup)
            else:
                mapper.SetLookupTable(lookup)
        mapper.SetUseLookupTableScalarRange(True)
        mapper.SetScalarRange(*legacy_mapper.GetScalarRange())
    except (AttributeError, RuntimeError, TypeError, ValueError):
        pass
    _configure_scalar_mapper(mapper, color, clim)
    return mapper


def _configure_scalar_mapper(mapper, color, clim):
    if color is None:
        mapper.ScalarVisibilityOff()
        return
    mapper.ScalarVisibilityOn()
    mapper.SetUseLookupTableScalarRange(True)
    mapper.SetScalarModeToUseCellFieldData()
    mapper.SetArrayName(str(color.name))
    mapper.SetArrayComponent(0)
    lookup = mapper.GetLookupTable()
    if lookup is not None:
        try:
            if color.magnitude:
                lookup.SetVectorModeToMagnitude()
            else:
                lookup.SetVectorModeToComponent()
                lookup.SetVectorComponent(0)
        except (AttributeError, RuntimeError, TypeError):
            pass
    if clim is not None:
        mapping = _gpu_color_mapping(color, clim)
        scalar_range = (
            mapping[2] if mapping is not None
            else tuple(float(value) for value in clim)
        )
        mapper.SetScalarRange(*scalar_range)
        if lookup is not None:
            lookup.SetRange(*scalar_range)
            lookup.Modified()

def build_element_shader_state(grid, color=None, clim=None):
    """Build batched element shaders for one fixed-topology result grid."""
    _register_cellgrid()
    if (
        grid is None
        or grid.GetNumberOfCells() <= 0
        or grid.GetNumberOfPoints() <= 0
    ):
        return None
    color = _coerce_color_field(grid, color)
    cell_types = _cell_types(grid)
    unique = tuple(int(value) for value in np.unique(cell_types))
    if any(cell_type not in ELEMENT_SHADERS for cell_type in unique):
        return None
    specs = tuple(ELEMENT_SHADERS[cell_type] for cell_type in unique)
    if color is not None and _color_values(grid, color) is None:
        return None

    partitions = _partition_specs(specs)
    batches = [
        _build_batch(grid, cell_types, group, color, clim)
        for group in partitions
    ]
    if any(batch is None for batch in batches):
        return None

    _remove_cross_partition_internal_faces(batches)

    from vtkmodules.vtkCommonDataModel import vtkPartitionedDataSetCollection

    dataset = vtkPartitionedDataSetCollection()
    dataset.SetNumberOfPartitionedDataSets(len(batches))
    for index, batch in enumerate(batches):
        dataset.GetPartitionedDataSet(index).SetPartition(0, batch.surface)
    state = ElementShaderState(dataset, batches, color)
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


def _build_batch(grid, cell_types, specs, color, clim=None):
    from vtkmodules.vtkCommonDataModel import vtkCellGrid
    from vtkmodules.util.numpy_support import vtk_to_numpy

    color_name = color.name if color is not None else ""
    association = color.association if color is not None else ""
    components = color.components if color is not None else 0
    template = _template(
        tuple(spec.vtk_cell_type for spec in specs),
        color_name,
        association,
        components,
    )
    source = vtkCellGrid()
    source.DeepCopy(template)
    points = vtk_to_numpy(grid.GetPoints().GetData())
    point_group = _group(source, "points")
    _overwrite_array(point_group, "coords", points, 3)
    point_group.SetVectors(point_group.GetArray("coords"))

    color_values = _gpu_color_values(grid, color, clim)
    if color is not None and color.association == "point":
        _overwrite_array(
            point_group,
            color.name,
            color_values,
            color.components,
        )

    offsets, connectivity = _connectivity(grid)
    cell_indices = {}
    batch_connectivity = {}
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
        cell_group.SetScalars(cell_group.GetArray("cell-connectivity"))
        if color is not None and color.association == "cell":
            selected = color_values[indices]
            _overwrite_array(
                cell_group,
                color.name,
                selected,
                color.components,
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
def _template(cell_types, color_name, association, components):
    specs = tuple(ELEMENT_SHADERS[int(cell_type)] for cell_type in cell_types)
    document = _template_document(
        specs,
        color_name or None,
        association or None,
        int(components or 0),
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


def _template_document(specs, color_name, association, components=1):
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
    if color_name and association == "point":
        point_arrays.append(
            {
                "components": components,
                "data": [0.0] * components,
                "name": color_name,
                "tuples": 1,
                "type": "double",
            }
        )
    arrays = {"points": point_arrays}
    shape_info = {}
    color_info = {}
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
        if color_name and association == "cell":
            type_arrays.append(
                {
                    "components": components,
                    "data": [0.0] * components,
                    "name": color_name,
                    "tuples": 1,
                    "type": "double",
                }
            )
        arrays[spec.dg_type] = type_arrays
        shape_info[spec.dg_type] = _hgrad_info(spec, "coords")
        if color_name:
            color_info[spec.dg_type] = (
                _hgrad_info(spec, color_name)
                if association == "point"
                else {
                    "arrays": {
                        "connectivity": [
                            spec.dg_type,
                            "cell-connectivity",
                        ],
                        "values": [spec.dg_type, color_name],
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
    if color_name:
        attributes.append(
            {
                "cell-info": color_info,
                "components": components,
                "name": color_name,
                "space": "ℝ" if components == 1 else "ℝ³",
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
