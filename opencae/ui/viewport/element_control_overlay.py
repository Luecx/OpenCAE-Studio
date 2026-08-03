import numpy as np

from .vtk_cell_data import cell_array
from .safe_operations import remove_actor


class ElementControlOverlay:
    def __init__(self): self.names = ("element-control-selected", "element-control-propagated")

    def clear(self, plotter):
        for name in self.names:
            remove_actor(plotter, name)

    def show(self, plotter, scene, selected=(), propagated=()):
        self.clear(plotter); grid = scene.mesh_grid
        ids = cell_array(grid, "element_id")
        if grid is None or not len(ids): return
        self._add(plotter, grid, ids, selected, self.names[0], "#3296e6", .72)
        self._add(plotter, grid, ids, propagated, self.names[1], "#f2a45d", .62)

    @staticmethod
    def _add(plotter, grid, ids, wanted, name, color, opacity):
        indices = np.where(np.isin(ids, tuple(wanted)))[0]
        if not len(indices): return
        try: mesh = grid.extract_cells(indices)
        except (RuntimeError, RecursionError, ValueError): return
        plotter.add_mesh(mesh, color=color, opacity=opacity, show_edges=True, line_width=1.5,
                         name=name, pickable=False, render=False)
