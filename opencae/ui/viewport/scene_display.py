"""Shared scene presentation behavior for model, live and stored results."""

from .field_visualization import add_field
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
        """Return whether two workflow stages can reuse the same base scene."""
        return (
            self._assembly_stage(previous) == self._assembly_stage(current)
            and current != "RESULTS"
            and previous != "RESULTS"
        )

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

    def fit(self):
        """Fit the camera only when the scene currently has renderable content."""
        if (
            self.face_actors
            or self.mesh_actor
            or self.mesh_actors
            or self.result_actor
        ):
            self.owner.plotter.view_isometric()
            self.owner.plotter.reset_camera()

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
        """Replace the base scene with one stored solver result presentation."""
        show_result(self, result, field, options)
