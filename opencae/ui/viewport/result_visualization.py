"""Build conventional result actors and deformation/range presentation data."""

import numpy as np

from opencae.results import FrdLoader
from .contour_mapping import contour_plot_kwargs
from .scalar_bar import scalar_bar_args

_LOADER = FrdLoader()


def add_result(plotter, result, field=None, options=None):
    """Add the primary pickable result actor plus non-pickable visual overlays."""
    options = options or {}
    step_id = field.metadata.get("step_id") if field else None
    frame_id = field.metadata.get("frame_id") if field else None
    original = _LOADER.pyvista_grid(result.source_file, step_id, frame_id)
    original = _animated_grid(original, result, field, options)
    grid = _deformed(original, options)
    scalar = _scalar_name(field)
    range_settings = options.get("range", {})
    clim = _clim(grid, scalar, range_settings)
    mapping = contour_plot_kwargs(range_settings)
    show_edges = bool(options.get("mesh_lines", True))
    actor = plotter.add_mesh(
        grid,
        scalars=scalar,
        clim=clim,
        cmap="turbo",
        n_colors=mapping["n_colors"],
        below_color=mapping["below_color"],
        above_color=mapping["above_color"],
        show_edges=False,
        edge_color="#182129",
        line_width=1.0,
        lighting=True,
        ambient=.22,
        diffuse=.76,
        smooth_shading=True,
        scalar_bar_args=scalar_bar_args(scalar, plotter) if scalar else None,
        name="solution-result",
        pickable=True,
        render=False,
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
        _boundary(
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
    """Return a transient frame with only displayed scalars/displacements animated."""
    animation = dict(options.get("_animation", {}) or {})
    mode = str(animation.get("mode", ""))
    if not mode or field is None:
        return grid
    scalar = _scalar_name(field)
    if mode == "factor":
        factor = min(max(float(animation.get("factor", 1.0)), 0.0), 1.0)
        animated = grid.copy(deep=True)
        scaled = set()
        if scalar and scalar in animated.point_data:
            animated.point_data[scalar] = np.asarray(animated.point_data[scalar], dtype=float) * factor
            scaled.add(scalar)
        keys = _displacement_keys(animated)
        if keys is not None:
            for key in keys:
                if key not in scaled:
                    animated.point_data[key] = np.asarray(animated.point_data[key], dtype=float) * factor
        return animated
    if mode != "interpolate":
        return grid

    next_field = animation.get("next_field")
    if next_field is None:
        return grid
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
    if (
        scalar
        and next_scalar
        and scalar in animated.point_data
        and next_scalar in next_grid.point_data
    ):
        animated.point_data[scalar] = interpolate_values(
            animated.point_data[scalar],
            next_grid.point_data[next_scalar],
            alpha,
        )

    keys = _displacement_keys(animated)
    next_keys = _displacement_keys(next_grid)
    if keys is not None and next_keys is not None:
        for key, next_key in zip(keys, next_keys):
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


def _mesh_edges(plotter, grid, name):
    try:
        edges = grid.extract_all_edges()
    except (AttributeError, RuntimeError, TypeError, ValueError):
        edges = grid.extract_surface(algorithm="dataset_surface").extract_feature_edges(
            boundary_edges=True,
            feature_edges=True,
            manifold_edges=True,
            non_manifold_edges=True,
            feature_angle=1,
        )
    return plotter.add_mesh(
        edges,
        color="#182129",
        line_width=1.0,
        lighting=False,
        name=name,
        pickable=False,
        render=False,
    )


def _boundary(
    plotter,
    grid,
    name,
    color="#f0f3f6",
    width=1.6,
    opacity=1.0,
):
    edges = grid.extract_surface(
        algorithm="dataset_surface"
    ).extract_feature_edges(
        boundary_edges=True,
        feature_edges=True,
        manifold_edges=False,
        non_manifold_edges=True,
        feature_angle=32,
    )
    return plotter.add_mesh(
        edges,
        color=color,
        opacity=opacity,
        line_width=width,
        lighting=False,
        name=name,
        pickable=False,
        render=False,
    )


def _scalar_name(field):
    return (
        f"{field.metadata.get('block', field.name)}:"
        f"{field.metadata.get('component', 'Magnitude')}"
        if field
        else None
    )


def _clim(grid, scalar, settings):
    if not scalar or scalar not in grid.point_data:
        return None
    values = np.asarray(grid.point_data[scalar])
    finite = values[np.isfinite(values)]
    if not len(finite):
        return None
    data_minimum, data_maximum = float(finite.min()), float(finite.max())
    minimum = (
        data_minimum
        if settings.get("minimum_auto", settings.get("auto", True))
        else float(settings.get("minimum", data_minimum))
    )
    maximum = (
        data_maximum
        if settings.get("maximum_auto", settings.get("auto", True))
        else float(settings.get("maximum", data_maximum))
    )
    if minimum > maximum:
        minimum, maximum = maximum, minimum
    if minimum == maximum:
        maximum = minimum + max(abs(minimum), 1.0) * 1e-12
    return minimum, maximum


def _deformed(grid, options):
    if not options.get("deform"):
        return grid
    keys = _displacement_keys(grid)
    if keys is None:
        return grid
    vectors = np.column_stack([grid.point_data[key] for key in keys])
    result = grid.copy(deep=True)
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
