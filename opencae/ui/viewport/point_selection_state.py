from __future__ import annotations

import numpy as np
from opencae.model.selection import SelectableKind, SelectionOperation, ViewportHit, ViewportSelection
from .picker_entities import actor_entity, selection_operation


class PointSelectionState:
    def __init__(self, owner):
        self.owner = owner
        self.selected: dict[tuple, ViewportHit] = {}
        self._name = "selected-points"

    def clear(self):
        self.selected.clear()
        self._remove()

    def picked(self, point):
        if point is None:
            return
        hit = self._nearest(np.asarray(point, float))
        if hit is None:
            return
        operation = selection_operation()
        if operation == SelectionOperation.REPLACE:
            self.selected = {hit.key: hit}
        elif operation == SelectionOperation.REMOVE:
            self.selected.pop(hit.key, None)
        else:
            self.selected[hit.key] = hit
        self._draw()
        self._emit(tuple(self.selected.values()), hit.with_operation(operation))

    def picked_node(self, point):
        self.picked(point)

    def _nearest(self, point):
        candidates = self._mesh_candidates(point) + self._actor_candidates(point)
        return min(candidates, key=lambda item: item[0])[1] if candidates else None

    def _mesh_candidates(self, point):
        if self.owner.display_mode != "mesh":
            return []
        context = self.owner.context_pick
        if context.active and not context.accepts(SelectableKind.MESH_NODE):
            return []
        result = []
        for instance_id, grid in [(None, self.owner.scene.mesh_grid), *self.owner.scene.mesh_grids.items()]:
            if grid is None or not grid.n_points:
                continue
            index = int(grid.find_closest_point(point))
            ids = np.asarray(grid.point_data.get("node_id", np.arange(grid.n_points)))
            node_id = int(ids[index])
            instance = self.owner.scene.instance_for(instance_id) if instance_id else None
            label = f"Node-{node_id}"
            if instance:
                label = f"{instance.name}.{label}"
            hit = ViewportHit(
                kind=SelectableKind.MESH_NODE,
                instance_id=instance_id,
                mesh_id=node_id,
                world_position=tuple(grid.points[index]),
                dimension=0,
                label=label,
            )
            result.append((float(np.linalg.norm(grid.points[index] - point)), hit))
        return result

    def _actor_candidates(self, point):
        result = []
        scene = self.owner.scene
        for actor in (*scene.vertex_actors, *scene.reference_actors, *scene.datum_actors):
            hit = actor_entity(scene, actor)
            if hit is None or hit.kind not in {
                SelectableKind.GEOMETRY_VERTEX,
                SelectableKind.REFERENCE_POINT,
                SelectableKind.DATUM_POINT,
            } or hit.world_position is None:
                continue
            if not _actor_enabled(actor):
                continue
            context = self.owner.context_pick
            if context.active and not context.accepts(hit.kind):
                continue
            result.append((float(np.linalg.norm(np.asarray(hit.world_position, float) - point)), hit))
        return result

    def _draw(self):
        self._remove()
        points = [value.world_position for value in self.selected.values() if value.world_position is not None]
        if points:
            self.owner.plotter.add_points(
                np.asarray(points),
                color="#3296e6",
                point_size=14,
                render_points_as_spheres=True,
                name=self._name,
                pickable=False,
                render=False,
            )

    def _remove(self):
        try:
            self.owner.plotter.remove_actor(self._name, reset_camera=False, render=False)
        except (KeyError, ValueError, RuntimeError) as exc:
            self.owner.message.emit(f"Could not clear point highlight: {exc}")

    def _emit(self, hits, event_hit):
        if self.owner.handle_entities((event_hit,)):
            # Region dialogs own the persistent preview.  Clear the temporary
            # point-picker marker after every gesture so the dialog overlay is
            # the single visual source of truth.
            self.clear()
        else:
            self.owner.selection_changed.emit(ViewportSelection.from_hits(hits) if hits else None)
        self.owner.plotter.render()


def _actor_enabled(actor):
    visibility = getattr(actor, "GetVisibility", lambda: True)()
    pickable = getattr(actor, "GetPickable", lambda: True)()
    return bool(visibility and pickable)
