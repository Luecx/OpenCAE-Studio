from __future__ import annotations

import numpy as np

from opencae.model.selection import (
    RegionProjection,
    SelectableKind,
    SelectionOperation,
    ViewportHit,
    ViewportSelection,
    element_side_indices,
)
from .picker_entities import selection_operation
from .vtk_cell_data import cell_array


class ElementSelectionState:
    def __init__(self, owner):
        self.owner = owner
        self.selected: dict[tuple, ViewportHit] = {}
        self._name = "selected-elements"

    def clear(self):
        self.selected.clear()
        self._remove_actor()

    def picked(self, point):
        candidate = self._nearest(point)
        if candidate is None:
            return
        instance_id, grid, cell_id = candidate
        ids = cell_array(grid, "element_id")
        if not len(ids):
            return
        element_id = int(ids[cell_id])
        local_face = self._facet_hit(instance_id, element_id, grid, cell_id, point)
        kind = SelectableKind.MESH_FACET if local_face else SelectableKind.MESH_ELEMENT
        instance = self.owner.scene.instance_for(instance_id) if instance_id else None
        suffix = f".{local_face}" if local_face else ""
        label = f"Element-{element_id}{suffix}"
        if instance:
            label = f"{instance.name}.{label}"
        hit = ViewportHit(
            kind=kind,
            instance_id=instance_id,
            mesh_id=element_id,
            local_face=local_face,
            world_position=tuple(np.asarray(point, float)),
            dimension=grid.get_cell(cell_id).dimension,
            label=label,
        )
        operation = selection_operation()
        if operation == SelectionOperation.REPLACE:
            self.selected = {hit.key: hit}
        elif operation == SelectionOperation.REMOVE:
            self.selected.pop(hit.key, None)
        else:
            self.selected[hit.key] = hit
        self._draw()
        self._emit(tuple(self.selected.values()), hit.with_operation(operation))

    def _facet_hit(self, instance_id, element_id, grid, cell_id, point):
        context = self.owner.context_pick
        if not context.active or SelectableKind.MESH_FACET not in context.allowed:
            return None
        if context.policy.requirement.projection != RegionProjection.FACETS:
            return None
        topology = self._topology(instance_id, element_id)
        sides = element_side_indices(topology)
        if not sides:
            return "SPOS" if grid.get_cell(cell_id).dimension == 2 else None
        points = np.asarray(grid.get_cell(cell_id).points, dtype=float)
        hit = np.asarray(point, dtype=float)
        scored = []
        for side, indices in sides:
            face = points[[index for index in indices if index < len(points)]]
            if len(face) < 3:
                continue
            center = face.mean(axis=0)
            normal = np.cross(face[1] - face[0], face[2] - face[0])
            norm = float(np.linalg.norm(normal))
            plane = abs(float(np.dot(hit - center, normal / norm))) if norm > 1e-14 else 0.0
            radial = float(np.linalg.norm(hit - center))
            scored.append((plane + 1e-3 * radial, side))
        return min(scored, default=(0.0, None))[1]

    def _topology(self, instance_id, element_id):
        instance = self.owner.scene.instance_for(instance_id) if instance_id else None
        part = self.owner.store.project.try_resolve(instance.part_ref) if instance else self.owner.store.active_part()
        if part is None:
            return ""
        for block in part.mesh.element_blocks:
            if int(element_id) in {int(value) for value in block.ids}:
                return block.definition.topology
        return ""

    def _nearest(self, point):
        candidates = []
        for instance_id, grid in [(None, self.owner.scene.mesh_grid), *self.owner.scene.mesh_grids.items()]:
            if grid is None or not grid.n_cells:
                continue
            cell_id = int(grid.find_closest_cell(point))
            center = np.asarray(grid.get_cell(cell_id).center)
            candidates.append((float(np.linalg.norm(center - np.asarray(point))), instance_id, grid, cell_id))
        return min(candidates, key=lambda item: item[0])[1:] if candidates else None

    def _remove_actor(self):
        try:
            self.owner.plotter.remove_actor(self._name, reset_camera=False, render=False)
        except (KeyError, ValueError, RuntimeError) as exc:
            self.owner.message.emit(f"Could not clear element highlight: {exc}")

    def _draw(self):
        self._remove_actor()
        meshes = []
        for hit in self.selected.values():
            grid = self.owner.scene.mesh_grids.get(hit.instance_id) if hit.instance_id else self.owner.scene.mesh_grid
            if grid is None:
                continue
            ids = cell_array(grid, "element_id")
            cells = np.where(ids == hit.mesh_id)[0]
            if len(cells):
                meshes.append(grid.extract_cells([int(cells[0])]))
        if meshes:
            import pyvista as pv

            self.owner.plotter.add_mesh(
                pv.merge(meshes),
                color="#3296e6",
                opacity=.72,
                show_edges=True,
                name=self._name,
                pickable=False,
                reset_camera=False,
                render=False,
            )

    def _emit(self, hits, event_hit):
        if self.owner.context_pick.consume((event_hit,)):
            self.clear()
            self.owner.plotter.render()
            return
        self.owner.selection_changed.emit(ViewportSelection.from_hits(hits) if hits else None)
        self.owner.plotter.render()
