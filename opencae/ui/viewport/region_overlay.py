from __future__ import annotations

import numpy as np
import pyvista as pv

from opencae.model.selection import RegionDefinition, RegionProjection, RegionRequirement, RegionResolver
from .vtk_cell_data import cell_array
from .safe_operations import remove_actor


class RegionOverlay:
    def __init__(self): self._names = []
    def clear(self, plotter):
        for name in self._names:
            remove_actor(plotter, name)
        self._names.clear()

    def show(self, plotter, scene, definition):
        self.clear(plotter)
        definition = RegionDefinition.from_values(definition)
        project = scene.owner.store.project
        nodes = RegionResolver(project).resolve(definition, RegionRequirement(RegionProjection.NODES, (0,1,2,3), 0))
        elements = RegionResolver(project).resolve(definition, RegionRequirement(RegionProjection.ELEMENTS, (0,1,2,3), 0))
        node_groups = {}
        for item in nodes.nodes: node_groups.setdefault(item.instance_id, set()).add(item.node_id)
        element_groups = {}
        for item in elements.elements: element_groups.setdefault(item.instance_id, set()).add(item.element_id)
        for instance_id, tags in node_groups.items(): self._nodes(plotter, scene, instance_id, tags)
        for instance_id, tags in element_groups.items(): self._elements(plotter, scene, instance_id, tags)

    @staticmethod
    def _grid(scene, instance_id): return scene.mesh_grids.get(instance_id) if instance_id else scene.mesh_grid

    def _nodes(self, plotter, scene, instance_id, tags):
        grid = self._grid(scene, instance_id)
        if grid is None: return
        try: ids = np.asarray(grid.point_data.get("node_id", ()))
        except (AttributeError, RuntimeError, RecursionError): return
        points = grid.points[np.isin(ids, list(tags))]
        if not len(points): return
        name = f"region-nodes-{instance_id or 'part'}"; self._names.append(name)
        plotter.add_mesh(pv.PolyData(points), color="#ffd166", point_size=12, render_points_as_spheres=True, lighting=False, name=name, render=False)

    def _elements(self, plotter, scene, instance_id, tags):
        grid = self._grid(scene, instance_id)
        if grid is None: return
        ids = cell_array(grid, "element_id"); indices = np.where(np.isin(ids, list(tags)))[0]
        if not len(indices): return
        name = f"region-elements-{instance_id or 'part'}"; self._names.append(name)
        plotter.add_mesh(grid.extract_cells(indices), color="#3296e6", opacity=0.65, show_edges=True, edge_color="#d9efff", lighting=True, name=name, render=False)
