"""Build conventional result actors and deformation/range presentation data."""

import numpy as np

from opencae.results import FrdLoader
from opencae.results.beam_physical_representation import (
    BEAM_CENTERLINE_CELL,
    PHYSICAL_BEAM_CELL,
)
from opencae.ui.core.theme import PALETTE
from .contour_mapping import contour_plot_kwargs
from .element_shader_rendering import (
    color_field,
    install_element_shader_mapper,
    is_element_shader_actor,
    update_element_shader_mapper,
)
from .scalar_bar import (
    install_scalar_bar_end_caps,
    scalar_bar_args,
    update_scalar_bar_title,
)
from .surface_shading import supports_surface_shading

_LOADER = FrdLoader()
_SOURCE_POINT_INDEX = "_opencae_source_point_index"
_DISPLAY_SCALAR = "_opencae_display_scalar"
_FRD_VTK_ORDERED = "_opencae_frd_vtk_ordered"

# CalculiX/CGX FRD uses a different high-order edge-node ordering than VTK.
# FEMaster writes exactly this FRD convention in FrdWriter::write_elements().
# These permutations are self-inverse, so applying them to FRD connectivity
# restores the canonical VTK_QUADRATIC_* ordering expected by PyVista/VTK.
_FRD_HEX20_TO_VTK = np.asarray((
    0, 1, 2, 3, 4, 5, 6, 7,
    8, 9, 10, 11,
    16, 17, 18, 19,
    12, 13, 14, 15,
), dtype=np.int64)
_FRD_WEDGE15_TO_VTK = np.asarray((
    0, 1, 2, 3, 4, 5,
    6, 7, 8,
    12, 13, 14,
    9, 10, 11,
), dtype=np.int64)


def add_result(plotter, result, field=None, options=None):
    """Add the primary pickable result actor plus non-pickable visual overlays."""
    options = options or {}
    original, grid = _result_grids(result, field, options)
    scalar = _scalar_name(field)
    range_settings = options.get("range", {})
    clim = _clim(
        grid,
        scalar,
        range_settings,
        nonnegative=_is_nonnegative_field(field),
    )
    display_scalar = _render_scalar(grid, scalar, clim)
    use_shape_functions = _use_shape_functions(options)
    shader_color = (
        _shader_color_field(grid, field, scalar, display_scalar)
        if use_shape_functions
        else None
    )
    mapping = contour_plot_kwargs(range_settings)
    show_edges = bool(options.get("mesh_lines", True))
    shaded_result = _supports_result_shading(grid)
    actor = plotter.add_mesh(
        grid,
        scalars=display_scalar,
        clim=clim,
        cmap="turbo",
        n_colors=mapping["n_colors"],
        below_color=mapping["below_color"],
        above_color=mapping["above_color"],
        show_edges=False,
        edge_color=PALETTE["mesh_lines"],
        line_width=1.0 if shaded_result else 2.4,
        lighting=shaded_result,
        ambient=.22 if shaded_result else 1.0,
        diffuse=.76 if shaded_result else 0.0,
        smooth_shading=shaded_result,
        render_lines_as_tubes=not shaded_result,
        scalar_bar_args=(
            scalar_bar_args(
                scalar,
                plotter,
                outside_colors=bool(mapping["below_color"] or mapping["above_color"]),
            )
            if scalar
            else None
        ),
        name="solution-result",
        pickable=True,
        render=False,
    )
    # Classic retains PyVista's existing triangulated VTK mapper. Only the
    # opt-in shape-function path replaces it with CellGrid's GPU FE interpolator.
    actor._opencae_render_interpolation = (
        "shape_functions" if use_shape_functions else "classic"
    )
    if use_shape_functions:
        install_element_shader_mapper(actor, grid, shader_color, clim)
    if scalar:
        install_scalar_bar_end_caps(
            plotter,
            scalar,
            below_color=mapping["below_color"],
            above_color=mapping["above_color"],
        )
    mesh_edges = (
        _mesh_edges(plotter, grid, "solution-mesh-lines")
        if show_edges
        else None
    )
    boundary = (
        _boundary(plotter, grid, "solution-boundaries")
        if options.get("boundary_lines", True)
        else None
    )
    undeformed = (
        _undeformed(
            plotter,
            original,
            "solution-undeformed",
            color="#9aa6af",
            width=1.1,
            opacity=.8,
        )
        if options.get("undeformed", False)
        else None
    )
    return actor, grid, mesh_edges, boundary, undeformed


def update_result(
    result_actor,
    mesh_actor,
    boundary_actor,
    undeformed_actor,
    result,
    field=None,
    options=None,
    *,
    plotter=None,
):
    """Update persistent result actors in-place for one animation frame."""
    if result_actor is None:
        return None
    options = options or {}
    original, grid = _result_grids(result, field, options)
    scalar = _scalar_name(field)
    clim = _clim(
        grid,
        scalar,
        options.get("range", {}),
        nonnegative=_is_nonnegative_field(field),
    )
    display_scalar = _render_scalar(grid, scalar, clim)
    use_shape_functions = _use_shape_functions(options)
    requested_mode = "shape_functions" if use_shape_functions else "classic"
    if getattr(
        result_actor, "_opencae_render_interpolation", requested_mode
    ) != requested_mode:
        # The animation fast path cannot change mapper implementations in
        # place. Let solution_scene rebuild the actor while preserving camera,
        # contour settings, selection and timeline state.
        return None
    shader_color = (
        _shader_color_field(grid, field, scalar, display_scalar)
        if use_shape_functions
        else None
    )

    if use_shape_functions and is_element_shader_actor(result_actor):
        mapper = update_element_shader_mapper(
            result_actor,
            grid,
            shader_color,
            clim,
        )
        if mapper is None:
            return None
    else:
        mapper = _replace_actor_input(result_actor, grid)
        if mapper is None:
            return None
        association = _scalar_association(grid, scalar)
        if scalar and association is not None:
            try:
                if association == "cell":
                    mapper.SetScalarModeToUseCellFieldData()
                else:
                    mapper.SetScalarModeToUsePointFieldData()
                mapper.SelectColorArray(display_scalar)
                mapper.ScalarVisibilityOn()
            except (AttributeError, RuntimeError, TypeError):
                pass
            if clim is not None:
                try:
                    mapper.SetScalarRange(*clim)
                    lookup = mapper.GetLookupTable()
                    if lookup is not None:
                        lookup.SetRange(*clim)
                        lookup.Modified()
                except (AttributeError, RuntimeError, TypeError):
                    pass
        else:
            try:
                mapper.ScalarVisibilityOff()
            except (AttributeError, RuntimeError):
                pass

    if plotter is not None and scalar:
        update_scalar_bar_title(plotter, scalar)
    if mesh_actor is not None:
        _update_line_actor(mesh_actor, grid, _mesh_edge_grid)
    if boundary_actor is not None:
        _update_line_actor(boundary_actor, grid, _boundary_grid)
    # Undeformed geometry is invariant for ordinary frame animation. If the beam
    # subset itself changes the whole scene is rebuilt rather than animated.
    del undeformed_actor, original
    return grid


def _use_shape_functions(options) -> bool:
    """One contour setting selects the complete result-rendering pipeline."""
    return (
        str((options or {}).get("range", {}).get("interpolation", "shape_functions"))
        == "shape_functions"
    )


def _result_grids(result, field, options):
    animation = dict(options.get("_animation", {}) or {})
    step_id = field.metadata.get("step_id") if field else None
    frame_id = field.metadata.get("frame_id") if field else None
    full = animation.get("source_grid")
    if full is None:
        full = _LOADER.pyvista_grid(result.source_file, step_id, frame_id)
    full = _vtk_ordered_frd_grid(full)
    full = _animated_grid(full, result, field, options)
    original = _beam_subset(full, bool(options.get("_physical_beams", False)))
    owns_transient_copy = str(animation.get("mode", "")) in {
        "factor",
        "interpolate",
    }
    return original, _deformed(
        original,
        options,
        copy_grid=not owns_transient_copy,
    )


def _vtk_ordered_frd_grid(grid):
    """Normalize FRD quadratic solids to canonical VTK local node ordering once.

    FEMaster writes CalculiX/CGX FRD type 4/5 connectivity. PyVista cells with
    VTK_QUADRATIC_HEXAHEDRON/WEDGE ids must instead use VTK's local edge-node
    order. Normalize the render-source grid in place and mark it so animation
    caches never repeat the O(n_cells) connectivity pass.
    """
    if grid is None or not getattr(grid, "n_cells", 0):
        return grid
    try:
        if _FRD_VTK_ORDERED in grid.field_data:
            marker = np.asarray(grid.field_data[_FRD_VTK_ORDERED]).reshape(-1)
            if len(marker) and int(marker[0]) == 1:
                return grid
    except (AttributeError, KeyError, TypeError, ValueError):
        pass

    try:
        cell_types = np.asarray(grid.celltypes, dtype=np.int64)
    except (AttributeError, TypeError, ValueError):
        return grid

    needs_hex = np.any(cell_types == 25)
    needs_wedge = np.any(cell_types == 26)
    if needs_hex or needs_wedge:
        try:
            from vtkmodules.util.numpy_support import vtk_to_numpy

            cells = grid.GetCells()
            offsets = np.asarray(
                vtk_to_numpy(cells.GetOffsetsArray()),
                dtype=np.int64,
            )
            connectivity = vtk_to_numpy(cells.GetConnectivityArray())
        except (AttributeError, ImportError, TypeError, ValueError):
            return grid

        for cell_index, vtk_type in enumerate(cell_types):
            if vtk_type == 25:
                order = _FRD_HEX20_TO_VTK
            elif vtk_type == 26:
                order = _FRD_WEDGE15_TO_VTK
            else:
                continue
            begin = int(offsets[cell_index])
            end = int(offsets[cell_index + 1])
            if end - begin != len(order):
                continue
            local = np.asarray(connectivity[begin:end], dtype=np.int64).copy()
            connectivity[begin:end] = local[order]

        cells.GetConnectivityArray().Modified()
        cells.Modified()
        grid.Modified()

    try:
        grid.field_data[_FRD_VTK_ORDERED] = np.asarray([1], dtype=np.uint8)
    except (AttributeError, KeyError, TypeError, ValueError):
        pass
    return grid


def _beam_subset(grid, physical: bool):
    """Select line or physical beam cells from the canonical FRD superset."""
    if PHYSICAL_BEAM_CELL not in grid.cell_data:
        return grid
    generated = np.asarray(grid.cell_data[PHYSICAL_BEAM_CELL], dtype=bool)
    if len(generated) != grid.n_cells:
        return grid
    if physical:
        centerline = (
            np.asarray(grid.cell_data[BEAM_CENTERLINE_CELL], dtype=bool)
            if BEAM_CENTERLINE_CELL in grid.cell_data
            else np.zeros(grid.n_cells, dtype=bool)
        )
        keep = generated | ~centerline
    else:
        keep = ~generated
    indices = np.flatnonzero(keep)
    if len(indices) == grid.n_cells:
        return grid
    return grid.extract_cells(indices)


def _supports_result_shading(grid) -> bool:
    """Return whether a result grid has polygonal surface cells to shade."""
    try:
        surface = grid.extract_surface(algorithm="dataset_surface")
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return False
    return supports_surface_shading(surface)


def _replace_actor_input(actor, dataset):
    """Replace one actor's dataset without destroying the actor or its render state."""
    try:
        mapper = actor.GetMapper()
    except (AttributeError, RuntimeError):
        mapper = getattr(actor, "mapper", None)
    if mapper is None:
        return None
    try:
        mapper.SetInputData(dataset)
        mapper.Modified()
    except (AttributeError, RuntimeError, TypeError):
        return None
    return mapper


def _update_line_actor(actor, grid, builder):
    """Move an existing line overlay without re-running VTK extraction filters."""
    try:
        mapper = actor.GetMapper()
    except (AttributeError, RuntimeError):
        mapper = getattr(actor, "mapper", None)
    if mapper is None:
        return None
    try:
        import pyvista as pv

        current = pv.wrap(mapper.GetInput())
        source_ids = np.asarray(
            current.point_data[_SOURCE_POINT_INDEX],
            dtype=np.int64,
        )
        if (
            len(source_ids) == current.n_points
            and len(source_ids)
            and int(source_ids.min()) >= 0
            and int(source_ids.max()) < grid.n_points
        ):
            current.points = np.asarray(grid.points)[source_ids]
            current.Modified()
            mapper.Modified()
            return mapper
    except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
        pass
    return _replace_actor_input(actor, builder(grid))


def interpolate_values(first, second, alpha):
    """Linearly interpolate equal-shaped result arrays without mutating either frame."""
    left = np.asarray(first, dtype=float)
    right = np.asarray(second, dtype=float)
    if left.shape != right.shape:
        raise ValueError("Result frames have incompatible value shapes")
    weight = min(max(float(alpha), 0.0), 1.0)
    return left + weight * (right - left)


def auto_deformation_scale(result, field=None, target_fraction=0.10):
    """Return a scale that makes maximum displacement a fraction of model size."""
    if result is None or not getattr(result, "source_file", None):
        return None
    step_id = field.metadata.get("step_id") if field else None
    frame_id = field.metadata.get("frame_id") if field else None
    grid = _LOADER.pyvista_grid(result.source_file, step_id, frame_id)
    keys = _displacement_keys(grid)
    if keys is None or grid.n_points == 0:
        return None
    vectors = np.column_stack([grid.point_data[key] for key in keys])
    magnitudes = np.linalg.norm(vectors, axis=1)
    finite = magnitudes[np.isfinite(magnitudes)]
    if not len(finite):
        return None
    maximum = float(finite.max())
    if maximum <= 1.0e-14:
        return None
    bounds = np.asarray(grid.bounds, dtype=float)
    diagonal = float(np.linalg.norm(bounds[1::2] - bounds[::2]))
    if diagonal <= 1.0e-14:
        diagonal = 1.0
    return target_fraction * diagonal / maximum


def _animated_grid(grid, result, field, options):
    """Return a transient frame with displayed primitive and derived data animated."""
    animation = dict(options.get("_animation", {}) or {})
    mode = str(animation.get("mode", ""))
    if not mode or field is None:
        return grid
    scalar = _scalar_name(field)
    if mode == "factor":
        factor = min(max(float(animation.get("factor", 1.0)), -1.0), 1.0)
        animated = grid.copy(deep=True)
        scaled = set()
        store = _scalar_store(animated, scalar)
        if scalar and store is not None:
            store[scalar] = np.asarray(store[scalar], dtype=float) * factor
            scaled.add(scalar)

        for key in _derived_shader_source_keys(animated, field):
            if key not in scaled:
                animated.point_data[key] = np.asarray(
                    animated.point_data[key], dtype=float
                ) * factor
                scaled.add(key)

        keys = _displacement_keys(animated)
        if keys is not None:
            for key in keys:
                if key not in scaled:
                    animated.point_data[key] = np.asarray(
                        animated.point_data[key], dtype=float
                    ) * factor
        return animated
    if mode != "interpolate":
        return grid

    next_field = animation.get("next_field")
    if next_field is None:
        return grid
    next_grid = animation.get("next_grid")
    if next_grid is None:
        next_grid = _LOADER.pyvista_grid(
            result.source_file,
            next_field.metadata.get("step_id"),
            next_field.metadata.get("frame_id"),
        )
    if not _compatible_frames(grid, next_grid):
        return grid
    alpha = min(max(float(animation.get("alpha", 0.0)), 0.0), 1.0)
    animated = grid.copy(deep=True)
    next_scalar = _scalar_name(next_field)
    current_store = _scalar_store(animated, scalar)
    next_store = _scalar_store(next_grid, next_scalar)
    if (
        scalar
        and next_scalar
        and current_store is not None
        and next_store is not None
        and scalar in current_store
        and next_scalar in next_store
    ):
        current_store[scalar] = interpolate_values(
            current_store[scalar],
            next_store[next_scalar],
            alpha,
        )

    derived_keys = _derived_shader_source_keys(animated, field)
    next_derived_keys = _derived_shader_source_keys(next_grid, next_field)
    if len(derived_keys) == len(next_derived_keys):
        for key, next_key in zip(derived_keys, next_derived_keys):
            animated.point_data[key] = interpolate_values(
                animated.point_data[key],
                next_grid.point_data[next_key],
                alpha,
            )

    keys = _displacement_keys(animated)
    next_keys = _displacement_keys(next_grid)
    if keys is not None and next_keys is not None:
        for key, next_key in zip(keys, next_keys):
            if key in derived_keys:
                continue
            animated.point_data[key] = interpolate_values(
                animated.point_data[key],
                next_grid.point_data[next_key],
                alpha,
            )
    return animated

def _compatible_frames(first, second):
    if first.n_points != second.n_points or first.n_cells != second.n_cells:
        return False
    if "node_id" in first.point_data and "node_id" in second.point_data:
        return bool(
            np.array_equal(
                np.asarray(first.point_data["node_id"]),
                np.asarray(second.point_data["node_id"]),
            )
        )
    return bool(np.allclose(first.points, second.points, equal_nan=True))


def _indexed_grid(grid):
    """Attach a source-point map that survives surface/edge extraction."""
    indexed = grid.copy(deep=False)
    indexed.point_data[_SOURCE_POINT_INDEX] = np.arange(
        indexed.n_points,
        dtype=np.int64,
    )
    return indexed


def _mesh_edge_grid(grid):
    indexed = _indexed_grid(grid)
    try:
        return indexed.extract_all_edges()
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return indexed.extract_surface(algorithm="dataset_surface").extract_feature_edges(
            boundary_edges=True,
            feature_edges=True,
            manifold_edges=True,
            non_manifold_edges=True,
            feature_angle=1,
        )


def _line_overlay(plotter, dataset, name, color, width, opacity=1.0):
    return plotter.add_mesh(
        dataset,
        color=color,
        opacity=opacity,
        line_width=width,
        lighting=False,
        name=name,
        pickable=False,
        render=False,
    )


def _mesh_edges(plotter, grid, name):
    return _line_overlay(
        plotter,
        _mesh_edge_grid(grid),
        name,
        PALETTE["mesh_lines"],
        1.0,
    )


def _undeformed(plotter, grid, name, color, width, opacity):
    """Show the undeformed topology even when the result consists only of lines."""
    return _line_overlay(
        plotter,
        _mesh_edge_grid(grid),
        name,
        color,
        width,
        opacity,
    )


def _boundary_grid(grid):
    return _indexed_grid(grid).extract_surface(
        algorithm="dataset_surface"
    ).extract_feature_edges(
        boundary_edges=True,
        feature_edges=True,
        manifold_edges=False,
        non_manifold_edges=True,
        feature_angle=32,
    )


def _boundary(
    plotter,
    grid,
    name,
    color="#f0f3f6",
    width=1.6,
    opacity=1.0,
):
    return _line_overlay(
        plotter,
        _boundary_grid(grid),
        name,
        color,
        width,
        opacity,
    )


def _field_component(field):
    if field is None:
        return ""
    return str(
        field.metadata.get(
            "component",
            field.metadata.get("default_component", "Magnitude"),
        )
    )


def _stress_component_keys(grid, block):
    prefix = f"{block}:"
    groups = (
        ("SXX",),
        ("SYY",),
        ("SZZ",),
        ("SXY",),
        ("SYZ",),
        ("SZX", "SXZ"),
    )
    keys = []
    for aliases in groups:
        key = next(
            (prefix + name for name in aliases if prefix + name in grid.point_data),
            None,
        )
        if key is None:
            return None
        keys.append(key)
    return tuple(keys)


def _derived_shader_source_keys(grid, field):
    if field is None:
        return ()
    component = _field_component(field).strip().casefold()
    block = str(field.metadata.get("block", field.name))
    if component == "magnitude":
        if block.upper().startswith("DISP"):
            return tuple(_displacement_keys(grid) or ())
        stress = _stress_component_keys(grid, block)
        if stress is not None:
            return stress
    if component == "mises":
        return tuple(_stress_component_keys(grid, block) or ())
    return ()


def _shader_color_field(grid, field, scalar, display_scalar):
    if not scalar:
        return None
    component = _field_component(field).strip().casefold()
    block = str(field.metadata.get("block", field.name)) if field is not None else ""
    if component == "magnitude":
        if block.upper().startswith("DISP"):
            keys = _displacement_keys(grid)
            if keys is not None:
                return color_field(grid, scalar, keys, magnitude=True)
        stress = _stress_component_keys(grid, block)
        if stress is not None:
            return color_field(grid, scalar, stress, magnitude=True)
    if component == "mises":
        stress = _stress_component_keys(grid, block)
        if stress is not None:
            return color_field(
                grid,
                scalar,
                stress,
                transform="mises",
                magnitude=True,
            )
    return color_field(grid, display_scalar)


def _is_nonnegative_field(field):
    component = _field_component(field).strip().casefold()
    return component in {"magnitude", "mises", "tresca"}

def _scalar_name(field):
    if field is None:
        return None
    component = field.metadata.get(
        "component",
        field.metadata.get("default_component", "Magnitude"),
    )
    return f"{field.metadata.get('block', field.name)}:{component}"


def _scalar_association(grid, scalar):
    if not scalar:
        return None
    if scalar in grid.point_data:
        return "point"
    if scalar in grid.cell_data:
        return "cell"
    return None


def _scalar_store(grid, scalar):
    association = _scalar_association(grid, scalar)
    if association == "point":
        return grid.point_data
    if association == "cell":
        return grid.cell_data
    return None


def _clim(grid, scalar, settings, *, nonnegative=False):
    store = _scalar_store(grid, scalar)
    if store is None:
        return None
    minimum_auto = settings.get("minimum_auto", settings.get("auto", True))
    maximum_auto = settings.get("maximum_auto", settings.get("auto", True))
    if (
        not minimum_auto
        and not maximum_auto
        and "minimum" in settings
        and "maximum" in settings
    ):
        minimum = float(settings["minimum"])
        maximum = float(settings["maximum"])
    else:
        values = np.asarray(store[scalar])
        finite = values[np.isfinite(values)]
        if not len(finite):
            return None
        data_minimum, data_maximum = float(finite.min()), float(finite.max())
        minimum = (
            (0.0 if nonnegative else data_minimum)
            if minimum_auto
            else float(settings.get("minimum", data_minimum))
        )
        maximum = (
            data_maximum
            if maximum_auto
            else float(settings.get("maximum", data_maximum))
        )
    if minimum > maximum:
        minimum, maximum = maximum, minimum
    if minimum == maximum:
        maximum = minimum + max(abs(minimum), 1.0) * 1e-12
    span = maximum - minimum
    padding = 1.0e-6 * span
    lower = minimum - padding
    upper = maximum + padding
    # A nonnegative field whose selected minimum is zero must start at zero,
    # even with a manually entered bound. Keep explicitly negative user bounds.
    if nonnegative and (minimum_auto or minimum >= 0.0):
        lower = max(0.0, lower)
    return lower, upper


def _render_scalar(grid, scalar, clim):
    """Create a render-only scalar nudged just inside exact display bounds."""
    store = _scalar_store(grid, scalar)
    if store is None or clim is None:
        return scalar
    minimum, maximum = (float(value) for value in clim)
    span = maximum - minimum
    if not np.isfinite(span) or span <= 0.0:
        return scalar

    scale = max(abs(minimum), abs(maximum), 1.0)
    epsilon = max(span * 1.0e-9, np.finfo(float).eps * scale * 64.0)
    epsilon = min(epsilon, span * 1.0e-6)
    if not np.isfinite(epsilon) or epsilon <= 0.0:
        return scalar

    displayed = np.asarray(store[scalar], dtype=float).copy()
    finite = np.isfinite(displayed)
    lower = finite & (displayed >= minimum - epsilon) & (displayed <= minimum + epsilon)
    upper = finite & (displayed >= maximum - epsilon) & (displayed <= maximum + epsilon)
    displayed[lower] = minimum + epsilon
    displayed[upper] = maximum - epsilon
    store[_DISPLAY_SCALAR] = displayed
    return _DISPLAY_SCALAR


def _deformed(grid, options, *, copy_grid=True):
    if not options.get("deform"):
        return grid
    keys = _displacement_keys(grid)
    if keys is None:
        return grid
    vectors = np.column_stack([grid.point_data[key] for key in keys])
    result = grid.copy(deep=True) if copy_grid else grid
    result.points = result.points + float(options.get("scale", 1.0)) * vectors
    return result


def _displacement_keys(grid):
    candidates = (
        ("DISP:D1", "DISP:D2", "DISP:D3"),
        ("DISPLACEMENT:Ux", "DISPLACEMENT:Uy", "DISPLACEMENT:Uz"),
        ("DISP:Ux", "DISP:Uy", "DISP:Uz"),
    )
    return next(
        (
            group
            for group in candidates
            if all(key in grid.point_data for key in group)
        ),
        None,
    )
