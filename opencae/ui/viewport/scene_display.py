from .field_visualization import add_field
from .solution_scene import show_result


class SceneDisplayMixin:
    @staticmethod
    def _assembly_stage(stage): return stage in {"ASSEMBLY", "CONSTRAINTS", "BOUNDARY CONDITIONS", "ANALYSIS", "SOLVE"}

    def same_display_context(self, previous, current):
        return self._assembly_stage(previous) == self._assembly_stage(current) and current != "RESULTS" and previous != "RESULTS"

    def update_stage_overlays(self, stage):
        self.boundary_overlay.clear(self.owner.plotter); self.coupling_overlay.clear(self.owner.plotter)
        if stage == "BOUNDARY CONDITIONS": self.boundary_overlay.show(self.owner.plotter, self.owner.store.project, self)
        if stage in {"CONSTRAINTS", "BOUNDARY CONDITIONS"}: self.coupling_overlay.show(self.owner.plotter, self.owner.store.project, self)
        self.owner.plotter.render()

    def _context_key(self): return self.owner.stage, self.part_id, tuple(sorted(self.assembly_snapshots))

    def fit(self):
        if self.face_actors or self.mesh_actor or self.mesh_actors or self.result_actor:
            self.owner.plotter.view_isometric(); self.owner.plotter.reset_camera()

    def show_seed_preview(self, seeds): self.seed_overlay.show(self.owner.plotter, self.snapshot, self.owner.store.active_part(), seeds)
    def hide_seed_preview(self): self.seed_overlay.clear(self.owner.plotter)

    def show_field(self, field):
        if self.mesh_grid is None: self.owner.message.emit("Generate a mesh before visualizing a field"); return
        self.field_actor = add_field(self.owner.plotter, self.mesh_grid, self.mesh_snapshot, field)

    def show_result(self, result, field=None, options=None): show_result(self, result, field, options)
