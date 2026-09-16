"""Shared scene presentation behavior for model, live and stored results."""

import numpy as np

from .beam_physical_display import beam_physical_controller
from .field_visualization import add_field
from .scene_camera import fit_camera
from .solution_scene import show_result


class SceneDisplayMixin:
    """Provide stage-context, overlay, field, and result presentation helpers."""

    @staticmethod
    def _assembly_stage(stage):
        return stage in {
            "ASSEMBLY",
            "CONSTRAINTS",
            "BOUNDARY CONDITIONS",
            "STEPS",
            "ANALYSIS",
            "STUDIES",
        }

    def same_display_context(self, previous, current):
        """Return whether two workflow stages can reuse the same base scene.

        Entering Results deliberately keeps the current scene alive until the
        selected ResultSet replaces it. Scheduling an intermediate base-scene
        rebuild here races result loading and can otherwise clear a freshly
        loaded FRD on the next Qt event turn.
        """
        if current == "RESULTS":
            return True
        if previous == "RESULTS":
            return False
        return self._assembly_stage(previous) == self._assembly_stage(current)

    def update_stage_overlays(self, stage):
        """Update only overlays whose visibility depends on the workflow stage."""
        if stage == "BOUNDARY CONDITIONS":
            self.boundary_overlay.show(
                self.owner.plotter,
                self.owner.store.project,
                self,
            )
        else:
            self.boundary_overlay.clear(self.owner.plotter)

        if stage in {"CONSTRAINTS", "BOUNDARY CONDITIONS"}:
            self.coupling_overlay.show(
                self.owner.plotter,
                self.owner.store.project,
                self,
            )
        else:
            self.coupling_overlay.clear(self.owner.plotter)
        self.owner.plotter.render()

    def _context_key(self):
        return self.owner.stage, self.part_id, tuple(sorted(self.assembly_snapshots))

    def fit(self, *, reset_orientation=False):
        """Frame the visible scene, including line/point-only result datasets."""
        return fit_camera(
            self.owner.plotter,
            points=self._fit_points(),
            reset_orientation=bool(reset_orientation),
            render=True,
        )

    def _fit_points(self):
        """Return geometry points when they represent the whole visible base scene.

        CAD, topology-density overlays, and mixed CAD/mesh scenes intentionally
        fall back to renderer bounds because their complete visible geometry is
        not centrally owned by one grid. Result and mesh-only scenes expose their
        points directly, which lets Fit View detect line/plane dimensionality and
        avoid end-on/edge-on framing.
        """
        if bool(getattr(getattr(self, "topology_overlay", None), "_names", ())):
            return None

        result_grid = getattr(self, "result_grid", None)
        if result_grid is not None:
            try:
                points = np.asarray(result_grid.points, dtype=float)
            except (AttributeError, TypeError, ValueError):
                points = None
            if points is not None and len(points):
                return points

        if getattr(self, "face_actors", None):
            return None

        grids = []
        for grid in (
            getattr(self, "mesh_grid", None),
            getattr(self, "authored_node_grid", None),
        ):
            if grid is not None:
                grids.append(grid)
        grids.extend(
            grid
            for grid in getattr(self, "mesh_grids", {}).values()
            if grid is not None
        )
        grids.extend(
            grid
            for grid in getattr(self, "authored_node_grids", {}).values()
            if grid is not None
        )

        arrays = []
        for grid in grids:
            try:
                values = np.asarray(grid.points, dtype=float)
            except (AttributeError, TypeError, ValueError):
                continue
            if len(values):
                arrays.append(values)
        if not arrays:
            return None
        return arrays[0] if len(arrays) == 1 else np.vstack(arrays)

    def show_seed_preview(self, seeds):
        """Display temporary mesh seed markers for the active Part."""
        self.seed_overlay.show(
            self.owner.plotter,
            self.snapshot,
            self.owner.store.active_part(),
            seeds,
        )

    def hide_seed_preview(self):
        """Clear temporary mesh seed markers."""
        self.seed_overlay.clear(self.owner.plotter)

    def show_field(self, field):
        """Visualize one Field on the active mesh when a mesh grid is available."""
        if self.mesh_grid is None:
            self.owner.message.emit(
                "Generate a mesh before visualizing a field"
            )
            return
        self.field_actor = add_field(
            self.owner.plotter,
            self.mesh_grid,
            self.mesh_snapshot,
            field,
        )

    def show_result(self, result, field=None, options=None):
        """Replace the base scene with one stored solver result presentation.

        Physical beams are inserted here rather than in one caller so ordinary
        field changes and Time Manager animation frames share the same expansion
        path and the same cached beam topology.
        """
        self.owner._active_result = result
        self.owner._active_result_field = field
        controller = beam_physical_controller(self.owner)
        controller.result_changed(result)
        prepared = controller.prepare_options(result, field, options)
        show_result(self, result, field, prepared)
