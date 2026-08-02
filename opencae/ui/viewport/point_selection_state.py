from __future__ import annotations

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from .picker_entities import actor_entity


class PointSelectionState:
    def __init__(self, owner): self.owner = owner; self.selected = {}; self._name = "selected-points"
    def clear(self): self.selected.clear(); self._remove()
    def picked(self, point):
        if point is None: return
        entity = self._nearest(np.asarray(point, float))
        if entity is None: return
        key = (entity.get("kind"), entity.get("instance"), entity.get("tag", entity.get("name")))
        if not self._additive(): self.selected.clear()
        if key in self.selected: self.selected.pop(key)
        else: self.selected[key] = entity
        self._draw(); self._emit(list(self.selected.values()))
    def picked_node(self, point): self.picked(point)
    def _nearest(self, point):
        candidates = self._mesh_candidates(point) + self._actor_candidates(point)
        return min(candidates, key=lambda item: item[0])[1] if candidates else None
    def _mesh_candidates(self, point):
        result = []
        for instance, grid in [(None, self.owner.scene.mesh_grid), *self.owner.scene.mesh_grids.items()]:
            if grid is None or not grid.n_points: continue
            index = int(grid.find_closest_point(point)); ids = np.asarray(grid.point_data.get("node_id", np.arange(grid.n_points)))
            tag = int(ids[index]); name = f"Node-{tag}"; name = f"{instance}.{name}" if instance else name
            entity = {"name":name,"kind":"node","dimension":0,"tag":tag,"instance":instance,
                      "mesh_entity":"node","point":tuple(grid.points[index])}
            result.append((float(np.linalg.norm(grid.points[index] - point)), entity))
        return result
    def _actor_candidates(self, point):
        result = []; scene = self.owner.scene
        for actor in (*scene.vertex_actors, *scene.reference_actors, *scene.datum_actors):
            entity = actor_entity(scene, actor)
            if not entity or entity.get("kind") not in {"vertex", "rp", "datum_point"} or not entity.get("point"): continue
            result.append((float(np.linalg.norm(np.asarray(entity["point"], float) - point)), entity))
        return result
    def _draw(self):
        self._remove(); points = [value.get("point") for value in self.selected.values() if value.get("point") is not None]
        if points:
            self.owner.plotter.add_points(np.asarray(points), color="#3296e6", point_size=14,
                                          render_points_as_spheres=True, name=self._name, pickable=False, render=False)
    def _remove(self):
        try: self.owner.plotter.remove_actor(self._name, reset_camera=False, render=False)
        except Exception: pass
    def _emit(self, entities):
        value = {"name": entities[0]["name"], "entities": entities} if entities else None
        if not self.owner.handle_entities(entities): self.owner.selection_changed.emit(value)
        self.owner.plotter.render()
    @staticmethod
    def _additive(): return bool(QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier)
