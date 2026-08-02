from __future__ import annotations

import numpy as np
import pyvista as pv

from .instance_transform import transform_points
from .surface_shading import mesh_cell_colors

_CELL_TYPES = {(1, 2): 3, (2, 3): 5, (2, 4): 9, (3, 4): 10, (3, 5): 14, (3, 6): 13, (3, 8): 12}


def build_grid(snapshot, instance=None):
    cells, cell_types, element_ids = [], [], []
    for block in snapshot.blocks:
        if block.dimension != snapshot.dimension: continue
        vtk_type = _CELL_TYPES.get((block.dimension, block.primary_nodes))
        if vtk_type is None: continue
        tags = block.element_tags if block.element_tags is not None else range(1, len(block.connectivity) + 1)
        for element_id, connectivity in zip(tags, block.connectivity):
            nodes = connectivity[:block.primary_nodes]
            cells.extend((len(nodes), *map(int, nodes))); cell_types.append(vtk_type); element_ids.append(int(element_id))
    if not cells: return None
    points = transform_points(snapshot.points, instance) if instance else snapshot.points
    grid = pv.UnstructuredGrid(np.asarray(cells, np.int64), np.asarray(cell_types, np.uint8), points)
    grid.point_data["node_id"] = snapshot.node_tags
    grid.cell_data["element_id"] = np.asarray(element_ids, dtype=np.int64)
    return grid


def add_mesh(plotter, snapshot, instance=None):
    grid = build_grid(snapshot, instance)
    if grid is None: return None, None
    surface = _display_surface(grid); surface.cell_data["display_rgb"] = mesh_cell_colors(surface)
    prefix = f"{instance.name}-" if instance else ""
    actor = plotter.add_mesh(
        surface, scalars="display_rgb", rgb=True, show_edges=False,
        lighting=True, smooth_shading=True, ambient=0.22, diffuse=0.76,
        specular=0.04, pickable=False,
        name=f"{prefix}generated-mesh-surface", render=False,
    )
    plotter.add_mesh(
        surface.extract_all_edges(), color="#182129", line_width=1.15,
        lighting=False, render_lines_as_tubes=False, pickable=False,
        name=f"{prefix}generated-mesh-lines", render=False,
    )
    return actor, grid


def _display_surface(grid):
    surface = grid.extract_surface(algorithm="dataset_surface")
    try:
        return surface.compute_normals(
            cell_normals=True, point_normals=True, split_vertices=True,
            consistent_normals=True, auto_orient_normals=False, inplace=False,
        )
    except Exception:
        return surface
