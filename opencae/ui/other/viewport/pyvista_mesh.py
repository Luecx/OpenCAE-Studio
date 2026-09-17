from __future__ import annotations

import numpy as np
import pyvista as pv

from opencae.model.entities.fem import MeshEntityOrigin
from opencae.ui.foundation.theme import PALETTE
from .instance_transform import transform_points
from .surface_shading import mesh_cell_colors, supports_surface_shading

_CELL_TYPES = {(1, 2): 3, (2, 3): 5, (2, 4): 9, (3, 4): 10, (3, 5): 14, (3, 6): 13, (3, 8): 12}


def build_grid(snapshot, instance=None, *, include_all_dimensions=False):
    """Build the viewport grid, optionally retaining lower-dimensional elements."""
    cells, cell_types, element_ids = [], [], []
    next_element_id = 1
    for block in snapshot.blocks:
        if not include_all_dimensions and block.dimension != snapshot.dimension:
            continue
        vtk_type = _CELL_TYPES.get((block.dimension, block.primary_nodes))
        if vtk_type is None:
            continue
        if block.element_tags is None:
            tags = range(next_element_id, next_element_id + len(block.connectivity))
        else:
            tags = [int(value) for value in block.element_tags]
        values = [int(value) for value in tags]
        if values:
            next_element_id = max(next_element_id, max(values) + 1)
        for element_id, connectivity in zip(values, block.connectivity):
            nodes = connectivity[:block.primary_nodes]
            cells.extend((len(nodes), *map(int, nodes)))
            cell_types.append(vtk_type)
            element_ids.append(element_id)
    if not cells:
        return None
    points = transform_points(snapshot.points, instance) if instance else snapshot.points
    grid = pv.UnstructuredGrid(np.asarray(cells, np.int64), np.asarray(cell_types, np.uint8), points)
    grid.point_data["node_id"] = snapshot.node_tags
    grid.cell_data["element_id"] = np.asarray(element_ids, dtype=np.int64)
    return grid


def build_authored_node_grid(part, instance=None):
    """Build a point-only dataset for nodes created explicitly by the user."""
    nodes = tuple(
        node
        for node in part.mesh.nodes
        if node.origin == MeshEntityOrigin.AUTHORED
    )
    if not nodes:
        return None
    points = np.asarray([node.coordinates for node in nodes], dtype=float)
    if instance is not None:
        points = transform_points(points, instance)
    grid = pv.PolyData(points)
    grid.point_data["node_id"] = np.asarray(
        [node.id for node in nodes],
        dtype=np.int64,
    )
    return grid


def add_authored_nodes(plotter, part, instance=None):
    """Render user-authored nodes persistently, independently of element cells."""
    grid = build_authored_node_grid(part, instance)
    if grid is None:
        return None, None
    prefix = f"{instance.name}-" if instance else ""
    actor = plotter.add_points(
        grid,
        color=PALETTE["cad_vertex"],
        point_size=11,
        render_points_as_spheres=True,
        lighting=False,
        pickable=False,
        name=f"{prefix}authored-mesh-nodes",
        reset_camera=False,
        render=False,
    )
    return actor, grid


def add_mesh(plotter, snapshot, instance=None, *, hidden_elements=()):
    grid = build_grid(snapshot, instance)
    if grid is None:
        return None, None
    hidden = {int(value) for value in hidden_elements}
    if hidden:
        ids = np.asarray(grid.cell_data["element_id"], dtype=np.int64)
        visible_indices = np.flatnonzero(~np.isin(ids, tuple(hidden)))
        grid = grid.extract_cells(visible_indices)
    prefix = f"{instance.name}-" if instance else ""
    if not grid.n_cells:
        return None, grid
    surface = _display_surface(grid)
    shaded_surface = supports_surface_shading(surface)
    surface.cell_data["display_rgb"] = mesh_cell_colors(surface)
    actor = plotter.add_mesh(
        surface,
        scalars="display_rgb",
        rgb=True,
        show_edges=False,
        lighting=shaded_surface,
        smooth_shading=shaded_surface,
        ambient=0.88 if shaded_surface else 1.0,
        diffuse=0.12 if shaded_surface else 0.0,
        specular=0.0,
        line_width=2.4 if not shaded_surface else 1.0,
        render_lines_as_tubes=not shaded_surface,
        pickable=False,
        name=f"{prefix}generated-mesh-surface",
        render=False,
    )
    if shaded_surface:
        plotter.add_mesh(
            surface.extract_all_edges(), color=PALETTE["mesh_lines"], line_width=1.35,
            lighting=False, render_lines_as_tubes=False, pickable=False,
            name=f"{prefix}generated-mesh-lines", render=False,
        )
    return actor, grid


def add_physical_mesh(plotter, grid, *, name):
    """Render one generated physical-beam surface without changing picker grids."""
    if grid is None or not int(getattr(grid, "n_cells", 0) or 0):
        return None
    surface = _display_surface(grid)
    shaded_surface = supports_surface_shading(surface)
    surface.cell_data["display_rgb"] = mesh_cell_colors(surface)
    return plotter.add_mesh(
        surface,
        scalars="display_rgb",
        rgb=True,
        show_edges=True,
        edge_color=PALETTE["mesh_lines"],
        line_width=1.1,
        lighting=shaded_surface,
        smooth_shading=shaded_surface,
        ambient=0.88 if shaded_surface else 1.0,
        diffuse=0.12 if shaded_surface else 0.0,
        specular=0.0,
        render_lines_as_tubes=False,
        pickable=False,
        name=str(name),
        reset_camera=False,
        render=False,
    )


def _display_surface(grid):
    surface = grid.extract_surface(algorithm="dataset_surface")
    if not supports_surface_shading(surface):
        return surface
    try:
        return surface.compute_normals(
            cell_normals=True, point_normals=True, split_vertices=True,
            consistent_normals=True, auto_orient_normals=False, inplace=False,
        )
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return surface
