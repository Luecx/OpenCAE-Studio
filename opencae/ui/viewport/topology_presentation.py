"""Shared topology-density presentation used by live monitors and Results."""

from __future__ import annotations

import numpy as np
import pyvista as pv

from opencae.geometry.cache import CACHE
from opencae.geometry.orphan_mesh import snapshot_from_part
from opencae.ui.core.theme import PALETTE
from .contour_mapping import contour_plot_kwargs
from .pyvista_mesh import build_grid
from .scalar_bar import scalar_bar_args
from .vtk_cell_data import cell_array
from .viewport_text_box import apply_viewport_text_box

_THRESHOLD_ABSOLUTE_TOLERANCE = 1.0e-9
_THRESHOLD_RELATIVE_TOLERANCE = 1.0e-9


def visible_density_indices(density, threshold):
    values = np.asarray(density, dtype=float).ravel()
    limit = float(threshold)
    tolerance = max(
        _THRESHOLD_ABSOLUTE_TOLERANCE,
        abs(limit) * _THRESHOLD_RELATIVE_TOLERANCE,
    )
    return np.flatnonzero(
        np.isfinite(values) & (values >= limit - tolerance)
    )


def topology_grid(project, mesh_index, density, threshold=0.30):
    """Build one merged assembly grid containing the visible density cells."""

    values = np.asarray(density, dtype=float).ravel()
    if len(values) != mesh_index.count:
        raise ValueError(
            "Saved topology density does not match the current mesh manifest"
        )
    pieces = []
    for instance in project.assembly.instances:
        if instance.suppressed:
            continue
        part = project.try_resolve(instance.part_ref)
        if part is None:
            continue
        snapshot = CACHE.mesh(part.id) or snapshot_from_part(part)
        if snapshot is None:
            continue
        grid = build_grid(snapshot, instance)
        if grid is None or not grid.n_cells:
            continue
        element_ids = cell_array(grid, "element_id")
        rows = np.flatnonzero(
            np.asarray(mesh_index.instance_ids) == str(instance.id)
        )
        lookup = {
            int(mesh_index.source_element_ids[row]): float(values[row])
            for row in rows
        }
        cell_density = np.asarray(
            [lookup.get(int(element_id), np.nan) for element_id in element_ids],
            dtype=float,
        )
        keep = visible_density_indices(cell_density, threshold)
        if not len(keep):
            continue
        copy = grid.copy(deep=False)
        copy.cell_data["Topology Density"] = cell_density
        pieces.append(copy.extract_cells(keep))
    if not pieces:
        return None
    return pv.merge(pieces, merge_points=False)


def topology_label(number, objective, density, threshold=0.30):
    values = np.asarray(density, dtype=float).ravel()
    finite = values[np.isfinite(values)]
    density_text = (
        f"ρ min/mean/max "
        f"{np.min(finite):.3f}/{np.mean(finite):.3f}/{np.max(finite):.3f}"
        if len(finite)
        else "ρ unavailable"
    )
    return (
        f"Iteration {int(number)}   Objective {float(objective):.6g}   "
        f"Threshold {float(threshold):.3f}   {density_text}"
    )


def add_topology_presentation(
    plotter,
    project,
    mesh_index,
    density,
    *,
    number,
    objective,
    threshold=0.30,
    options=None,
    name_prefix="topology-density",
):
    """Add the common density mesh, Colorbar, edge actors and iteration text."""

    options = options or {}
    grid = topology_grid(project, mesh_index, density, threshold)
    actor = mesh_actor = boundary_actor = None
    names = []
    if grid is not None:
        scalar_range = options.get("range", {})
        minimum = (
            0.0
            if scalar_range.get("minimum_auto", scalar_range.get("auto", True))
            else float(scalar_range.get("minimum", 0.0))
        )
        maximum = (
            1.0
            if scalar_range.get("maximum_auto", scalar_range.get("auto", True))
            else float(scalar_range.get("maximum", 1.0))
        )
        if minimum > maximum:
            minimum, maximum = maximum, minimum
        if minimum == maximum:
            maximum = minimum + max(abs(minimum), 1.0) * 1.0e-12
        mapping = contour_plot_kwargs(scalar_range)
        actor_name = f"{name_prefix}-surface"
        actor = plotter.add_mesh(
            grid,
            scalars="Topology Density",
            preference="cell",
            clim=(minimum, maximum),
            cmap="viridis",
            n_colors=mapping["n_colors"],
            below_color=mapping["below_color"],
            above_color=mapping["above_color"],
            show_edges=False,
            lighting=True,
            ambient=0.72,
            diffuse=0.28,
            specular=0.0,
            name=actor_name,
            pickable=False,
            reset_camera=False,
            render=False,
            scalar_bar_args=scalar_bar_args(
                "Density",
                plotter,
                outside_colors=bool(mapping["below_color"] or mapping["above_color"]),
            ),
        )
        names.append(actor_name)
        if options.get("mesh_lines", True):
            line_name = f"{name_prefix}-mesh-lines"
            mesh_actor = plotter.add_mesh(
                grid.extract_all_edges(),
                color=PALETTE["mesh_lines"],
                line_width=0.8,
                lighting=False,
                name=line_name,
                pickable=False,
                render=False,
            )
            names.append(line_name)
        if options.get("boundary_lines", True):
            boundary_name = f"{name_prefix}-boundaries"
            boundary = grid.extract_surface(
                algorithm="dataset_surface"
            ).extract_feature_edges(
                boundary_edges=True,
                feature_edges=True,
                manifold_edges=False,
                non_manifold_edges=True,
                feature_angle=32,
            )
            boundary_actor = plotter.add_mesh(
                boundary,
                color="#f0f3f6",
                line_width=1.4,
                lighting=False,
                name=boundary_name,
                pickable=False,
                render=False,
            )
            names.append(boundary_name)
    label_name = f"{name_prefix}-label"
    label_actor = plotter.add_text(
        topology_label(number, objective, density, threshold),
        position="upper_left",
        font_size=10,
        name=label_name,
        render=False,
    )
    apply_viewport_text_box(label_actor)
    names.append(label_name)
    return actor, grid, mesh_actor, boundary_actor, names
