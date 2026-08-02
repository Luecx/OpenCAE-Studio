from __future__ import annotations

import re
import numpy as np
import pyvista as pv

_LABEL = re.compile(r"^(?:(?P<instance>[^.]+)\.)?(?P<kind>Node|Element)-(?P<tag>\d+)$", re.I)


class RegionOverlay:
    def __init__(self): self._names = []
    def clear(self, plotter):
        for name in self._names:
            try: plotter.remove_actor(name, reset_camera=False, render=False)
            except Exception: pass
        self._names.clear()
    def show(self, plotter, scene, labels):
        self.clear(plotter); nodes = {}; elements = {}
        for value in labels:
            match = _LABEL.match(str(value))
            if not match: continue
            target = nodes if match.group("kind").lower() == "node" else elements
            target.setdefault(match.group("instance"), set()).add(int(match.group("tag")))
        for instance, tags in nodes.items(): self._nodes(plotter, scene, instance, tags)
        for instance, tags in elements.items(): self._elements(plotter, scene, instance, tags)
    def _grid(self, scene, instance): return scene.mesh_grids.get(instance) if instance else scene.mesh_grid
    def _nodes(self, plotter, scene, instance, tags):
        grid = self._grid(scene, instance)
        if grid is None or "node_id" not in grid.point_data: return
        ids = np.asarray(grid.point_data["node_id"]); mask = np.isin(ids, list(tags)); points = grid.points[mask]
        if not len(points): return
        name = f"region-nodes-{instance or 'part'}"; self._names.append(name)
        plotter.add_mesh(pv.PolyData(points), color="#ffd166", point_size=12, render_points_as_spheres=True, lighting=False, name=name, render=False)
    def _elements(self, plotter, scene, instance, tags):
        grid = self._grid(scene, instance)
        if grid is None or "element_id" not in grid.cell_data: return
        ids = np.asarray(grid.cell_data["element_id"]); indices = np.where(np.isin(ids, list(tags)))[0]
        if not len(indices): return
        name = f"region-elements-{instance or 'part'}"; self._names.append(name)
        plotter.add_mesh(grid.extract_cells(indices), color="#3296e6", opacity=0.65, show_edges=True, edge_color="#d9efff", lighting=True, name=name, render=False)
