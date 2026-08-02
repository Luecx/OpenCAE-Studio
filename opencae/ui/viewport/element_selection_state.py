from __future__ import annotations

import numpy as np

from .picker_entities import additive_selection


class ElementSelectionState:
    def __init__(self, owner): self.owner = owner; self.selected = {}; self._name = "selected-elements"

    def clear(self):
        self.selected.clear()
        try: self.owner.plotter.remove_actor(self._name, reset_camera=False, render=False)
        except Exception: pass

    def picked(self, point):
        candidate = self._nearest(point)
        if candidate is None: return
        instance, grid, cell_id = candidate; ids = np.asarray(grid.cell_data.get("element_id", ()))
        if not len(ids): return
        tag = int(ids[cell_id]); key = (instance, tag)
        if not additive_selection(): self.selected.clear()
        if key in self.selected: self.selected.pop(key)
        else:
            name = f"Element-{tag}"; name = f"{instance}.{name}" if instance else name
            self.selected[key] = {"name": name, "kind": "element", "dimension": grid.get_cell(cell_id).dimension,
                                  "tag": tag, "instance": instance, "mesh_entity": "element",
                                  "point": tuple(grid.get_cell(cell_id).center)}
        self._draw(); self._emit(list(self.selected.values()))

    def _nearest(self, point):
        candidates = []
        for instance, grid in [(None, self.owner.scene.mesh_grid), *self.owner.scene.mesh_grids.items()]:
            if grid is None or not grid.n_cells: continue
            cell_id = int(grid.find_closest_cell(point)); center = np.asarray(grid.get_cell(cell_id).center)
            candidates.append((float(np.linalg.norm(center - np.asarray(point))), instance, grid, cell_id))
        return min(candidates, key=lambda item: item[0])[1:] if candidates else None

    def _draw(self):
        try: self.owner.plotter.remove_actor(self._name, reset_camera=False, render=False)
        except Exception: pass
        meshes = []
        for (instance, tag) in self.selected:
            grid = self.owner.scene.mesh_grids.get(instance) if instance else self.owner.scene.mesh_grid
            ids = np.asarray(grid.cell_data.get("element_id", ())) if grid is not None else np.asarray([])
            hits = np.where(ids == tag)[0]
            if len(hits): meshes.append(grid.extract_cells([int(hits[0])]))
        if meshes:
            import pyvista as pv
            self.owner.plotter.add_mesh(pv.merge(meshes), color="#3296e6", opacity=.72, show_edges=True,
                                        name=self._name, pickable=False, render=False)

    def _emit(self, entities):
        if self.owner.context_pick.consume(entities): self.clear(); self.owner.plotter.render(); return
        value = {"name": entities[0]["name"], "entities": entities} if entities else None
        self.owner.selection_changed.emit(value); self.owner.plotter.render()
