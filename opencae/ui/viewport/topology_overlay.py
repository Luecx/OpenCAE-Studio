"""Live topology-density overlay built from the shared Results presentation."""

from __future__ import annotations

from .safe_operations import remove_actor
from .topology_presentation import (
    add_topology_presentation,
    visible_density_indices,
)


class TopologyDensityOverlay:
    """Display one topology iteration without owning an independent renderer."""

    def __init__(self):
        self._names: list[str] = []
        self._hidden_base_actors = []

    def clear(self, viewport, *, render=True):
        plotter = getattr(viewport, "plotter", None)
        if plotter is None:
            return
        for name in self._names:
            remove_actor(plotter, name)
        self._names.clear()
        for actor in self._hidden_base_actors:
            try:
                actor.SetVisibility(True)
            except (AttributeError, RuntimeError):
                pass
        self._hidden_base_actors.clear()
        if render:
            plotter.render()

    def show(
        self,
        viewport,
        run,
        iteration,
        mesh_index,
        density,
        *,
        threshold=0.30,
    ):
        self.clear(viewport, render=False)
        scene = viewport.scene
        for actor in [scene.mesh_actor, *scene.mesh_actors]:
            if actor is None:
                continue
            try:
                actor.SetVisibility(False)
                self._hidden_base_actors.append(actor)
            except (AttributeError, RuntimeError):
                pass
        _actor, _grid, _mesh, _boundary, names = add_topology_presentation(
            viewport.plotter,
            viewport.store.project,
            mesh_index,
            density,
            number=iteration.number,
            objective=iteration.objective_value,
            threshold=threshold,
            options={"mesh_lines": True, "boundary_lines": True},
            name_prefix="topology-live",
        )
        self._names.extend(names)
        viewport.plotter.render()
