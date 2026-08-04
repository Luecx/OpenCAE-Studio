from opencae.geometry.cache import CACHE
from opencae.geometry.errors import GeometryError
from opencae.ui.core.theme import PALETTE
from .boundary_overlay import BoundaryOverlay
from .coordinate_system_overlay import CoordinateSystemOverlay
from .pyvista_geometry import add_geometry
from .pyvista_mesh import add_mesh
from .seed_overlay import SeedOverlay
from .region_overlay import RegionOverlay
from .selection_preview_overlay import SelectionPreviewOverlay
from .reference_point_overlay import ReferencePointOverlay
from .datum_overlay import DatumOverlay
from .coupling_overlay import CouplingOverlay
from opencae.geometry.orphan_mesh import snapshot_from_part
from .scene_camera import camera_position, restore_camera
from .scene_display import SceneDisplayMixin
class PyVistaScene(SceneDisplayMixin):
    def __init__(self, owner):
        self.owner = owner; self.snapshot = None; self.part_id = None
        self.assembly_snapshots = {}; self.assembly_instances = {}
        self.face_actors = {}; self.edge_actors = {}; self.vertex_actors = {}; self.reference_actors = {}; self.datum_actors = {}
        self.mesh_actor = None; self.mesh_grid = None; self.mesh_snapshot = None
        self.mesh_actors = []; self.mesh_grids = {}; self.assembly_mesh_snapshots = {}
        self.seed_overlay = SeedOverlay(); self.coordinate_overlay = CoordinateSystemOverlay(); self.reference_overlay = ReferencePointOverlay(); self.datum_overlay = DatumOverlay(); self.coupling_overlay = CouplingOverlay(); self.region_overlay = RegionOverlay(); self.selection_preview_overlay = SelectionPreviewOverlay()
        self.boundary_overlay = BoundaryOverlay(owner); self.field_actor = None
        self.result_actor = None; self.result_grid = None; self.result_mesh_actor = None; self.result_boundary_actor = None; self.result_undeformed_actor = None
    def refresh(self, part, fit=False):
        camera = camera_position(self.owner.plotter); previous = self._context_key()
        self.clear(render=False); self.part_id = getattr(part, "id", None)
        if self._uses_assembly(): self._show_assembly()
        else: self._show_part(part)
        current = self._context_key()
        if fit or previous != current or camera is None: self.fit()
        else: restore_camera(self.owner.plotter, camera)
        self.owner.plotter.render()
    def clear(self, render=True):
        self.owner.section_view.clear_scene()
        self.seed_overlay.clear(self.owner.plotter, render=False)
        self.coordinate_overlay.clear(self.owner.plotter); self.reference_overlay.clear(self.owner.plotter); self.datum_overlay.clear(self.owner.plotter); self.coupling_overlay.clear(self.owner.plotter); self.boundary_overlay.clear(self.owner.plotter); self.region_overlay.clear(self.owner.plotter); self.selection_preview_overlay.clear(self.owner.plotter)
        self.owner.plotter.clear(); self.owner.plotter.set_background(PALETTE["viewport"])
        self.owner.canvas.meshability.hide()
        self.face_actors.clear(); self.edge_actors.clear(); self.vertex_actors.clear(); self.reference_actors.clear(); self.datum_actors.clear()
        self.assembly_snapshots.clear(); self.assembly_instances.clear(); self.mesh_actors.clear(); self.mesh_grids.clear(); self.assembly_mesh_snapshots.clear()
        self.mesh_actor = self.mesh_grid = self.mesh_snapshot = self.snapshot = None
        self.field_actor = self.result_actor = self.result_grid = self.result_mesh_actor = self.result_boundary_actor = self.result_undeformed_actor = None; self.owner.picker.reset()
        if render: self.owner.plotter.render()
    def _show_part(self, part):
        if part is None: return
        if part.geometry:
            try: self.snapshot = self.owner.service.build_geometry(part)
            except GeometryError as exc: self.owner.message.emit(str(exc)); return
        if self.owner.display_mode == "mesh" or not part.geometry: self._show_part_mesh(part)
        elif self.snapshot is not None:
            self._merge_actors(add_geometry(self.owner.plotter, self.snapshot, color_by_meshability=True))
            self._show_meshability_legend()
        self.coordinate_overlay.show_part(self.owner.plotter, part); self.reference_overlay.show_part(self.owner.plotter, part, self); self.datum_overlay.show_part(self.owner.plotter, part, self)
        self.owner.plotter.add_axes(color="#dce3e8"); self.owner.picker.configure()
    def _show_assembly(self):
        project = self.owner.store.project; instances = [item for item in project.assembly.instances if not item.suppressed]
        for instance in instances:
            part = project.try_resolve(instance.part_ref)
            if part is None: continue
            snapshot = None
            if part.geometry:
                try: snapshot = self.owner.service.build_geometry(part)
                except GeometryError as exc: self.owner.message.emit(str(exc)); continue
            if snapshot is not None: self.assembly_snapshots[instance.id] = snapshot
            self.assembly_instances[instance.id] = instance
            if self.owner.display_mode == "mesh" or not part.geometry: self._show_instance_mesh(part, instance)
            elif snapshot is not None: self._merge_actors(add_geometry(self.owner.plotter, snapshot, instance, color_by_meshability=False))
        self.coordinate_overlay.show_assembly(self.owner.plotter, project, self)
        self.reference_overlay.show_assembly(self.owner.plotter, project, self); self.datum_overlay.show_assembly(self.owner.plotter, project, self)
        if self.owner.stage == "BOUNDARY CONDITIONS": self.boundary_overlay.show(self.owner.plotter, project, self)
        if self.owner.stage in {"CONSTRAINTS", "BOUNDARY CONDITIONS"}: self.coupling_overlay.show(self.owner.plotter, project, self)
        self.owner.plotter.add_axes(color="#dce3e8"); self.owner.picker.configure()

    def _show_meshability_legend(self):
        visible = (
            self.owner.stage == "PART"
            and self.owner.display_mode == "geometry"
            and self.snapshot is not None
        )
        self.owner.canvas.meshability.setVisible(visible)
        self.owner.canvas._position_overlays()

    def _show_part_mesh(self, part):
        snapshot = CACHE.mesh(part.id) or snapshot_from_part(part)
        if snapshot is None and part.mesh.status == "Current":
            try: snapshot, _ = self.owner.service.generate_mesh(part)
            except GeometryError as exc: self.owner.message.emit(str(exc))
        if snapshot is None:
            if self.snapshot is not None: self._merge_actors(add_geometry(self.owner.plotter, self.snapshot, color_by_meshability=True))
            self.owner.message.emit("No generated mesh"); return
        self.mesh_snapshot = snapshot; self.mesh_actor, self.mesh_grid = add_mesh(self.owner.plotter, snapshot)
    def _show_instance_mesh(self, part, instance):
        snapshot = CACHE.mesh(part.id) or snapshot_from_part(part)
        if snapshot is None:
            geometry = self.assembly_snapshots.get(instance.id)
            if geometry is not None: self._merge_actors(add_geometry(self.owner.plotter, geometry, instance, color_by_meshability=False))
            return
        actor, grid = add_mesh(self.owner.plotter, snapshot, instance)
        if actor is not None:
            self.mesh_actors.append(actor); self.mesh_grids[instance.id] = grid; self.assembly_mesh_snapshots[instance.id] = snapshot
    def _merge_actors(self, actors):
        faces, edges, vertices = actors
        self.face_actors.update(faces); self.edge_actors.update(edges); self.vertex_actors.update(vertices)
    def snapshot_for(self, instance_key):
        if not instance_key:
            return self.snapshot
        return self.assembly_snapshots.get(instance_key)
    def instance_for(self, instance_key):
        if not instance_key:
            return None
        return self.assembly_instances.get(instance_key)
    def _uses_assembly(self): return self.owner.stage in {"ASSEMBLY", "CONSTRAINTS", "BOUNDARY CONDITIONS", "ANALYSIS", "SOLVE"}
