from .cell_selection import pick_cell
from .element_selection_state import ElementSelectionState
from .picker_entities import actor_entity, actor_kind, additive_selection
from .point_selection_state import PointSelectionState
from .pyvista_geometry import set_actor_selected


class PyVistaPicker:
    def __init__(self, owner):
        self.owner = owner; self.selected_actors = set(); self.selected_cells = set()
        self.points = PointSelectionState(owner); self.elements = ElementSelectionState(owner)
    def enable(self): self.configure()
    def configure(self):
        try: self.owner.plotter.disable_picking()
        except Exception: pass
        mode = self.owner.selection_mode
        if self.owner.stage == "RESULTS":
            self.update_pickability(); return
        try:
            if mode == "point":
                self.owner.plotter.enable_point_picking(callback=self.points.picked, left_clicking=True, show_message=False, show_point=False, picker="point", pickable_window=False)
            elif mode == "element" or (mode == "auto" and self.owner.display_mode == "mesh"):
                self.owner.plotter.enable_surface_point_picking(callback=self.elements.picked, left_clicking=True, show_message=False, show_point=False, picker="cell", pickable_window=False)
            else:
                self.owner.plotter.enable_mesh_picking(callback=self.picked_actor, use_actor=True, show=False, show_message=False, picker="hardware", left_clicking=True)
        except Exception: pass
        self.update_pickability()
    def clear(self, emit=True, render=True):
        for actor in tuple(self.selected_actors): set_actor_selected(actor, False, actor_kind(self.owner.scene, actor))
        self.selected_actors.clear(); self.selected_cells.clear(); self.points.clear(); self.elements.clear()
        if emit: self.owner.selection_changed.emit(None)
        if render: self.owner.plotter.render()
    def reset(self):
        self.selected_actors.clear(); self.selected_cells.clear(); self.points.clear(); self.elements.clear()
    def picked_actor(self, actor):
        scene = self.owner.scene; kind = actor_kind(scene, actor)
        valid = actor in scene.face_actors or actor in scene.edge_actors or actor in scene.vertex_actors or actor in scene.reference_actors or actor in scene.datum_actors
        if not valid: return
        if self.owner.selection_mode == "cell": pick_cell(self, actor); return
        allowed = self.owner.selection_mode in {"auto", kind} or (self.owner.selection_mode == "point" and kind in {"vertex","rp","datum_point"})
        if not allowed: return
        if not additive_selection(): self.clear(False, False)
        if actor in self.selected_actors:
            self.selected_actors.remove(actor); set_actor_selected(actor, False, kind)
        else:
            self.selected_actors.add(actor); set_actor_selected(actor, True, kind)
        self.emit_entities([item for item in (actor_entity(scene, current) for current in self.selected_actors) if item])
    def emit_entities(self, entities):
        if self.owner.handle_entities(entities): self.clear(False, False)
        else:
            value = {"name": entities[0]["name"], "entities": entities} if entities else None; self.owner.selection_changed.emit(value)
        self.owner.plotter.render()
    def show_labels(self, labels, render=True):
        from opencae.model.core import region_member_label
        project = self.owner.store.project
        self.clear(False, False); wanted = {region_member_label(project, value) for value in labels}
        actors = (*self.owner.scene.face_actors, *self.owner.scene.edge_actors, *self.owner.scene.vertex_actors, *self.owner.scene.reference_actors, *self.owner.scene.datum_actors)
        for actor in actors:
            entity = actor_entity(self.owner.scene, actor)
            if entity and entity["name"] in wanted:
                self.selected_actors.add(actor); set_actor_selected(actor, True, actor_kind(self.owner.scene, actor))
        for label in (value for value in wanted if ".Cell-" in value or value.startswith("Cell-")):
            prefix, raw = label.rsplit(".", 1) if "." in label else (None, label)
            try: self.selected_cells.add((prefix, int(raw.split("-", 1)[1])))
            except Exception: continue
        for actor, reference in self.owner.scene.face_actors.items():
            instance = getattr(reference, "instance_name", None); tag = getattr(reference, "tag", reference)
            snapshot = self.owner.scene.snapshot_for(instance)
            active = snapshot and any(inst == instance and cell in snapshot.surface_to_cells.get(tag, ()) for inst, cell in self.selected_cells)
            if active: self.selected_actors.add(actor); set_actor_selected(actor, True, "face")
        if render: self.owner.plotter.render()
    def update_pickability(self):
        mode = self.owner.selection_mode; scene = self.owner.scene
        if self.owner.stage == "RESULTS": mode = "none"
        for actor in scene.face_actors: actor.SetPickable(mode in {"auto","face","cell"})
        for actor in scene.edge_actors: actor.SetPickable(mode in {"auto","edge"})
        for actor in scene.vertex_actors: actor.SetPickable(mode in {"auto","point"}); actor.SetVisibility(mode in {"auto","point"})
        for actor in scene.reference_actors: actor.SetPickable(mode in {"auto","point"})
        for actor, ref in scene.datum_actors.items(): actor.SetPickable(mode == "auto" or (mode == "point" and ref.get("kind") == "datum_point"))
        if scene.mesh_actor is not None: scene.mesh_actor.SetPickable(mode in {"point","element"})
        for actor in scene.mesh_actors: actor.SetPickable(mode in {"point","element"})
