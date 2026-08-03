from .cell_selection import pick_cell
from .element_selection_state import ElementSelectionState
from .picker_entities import actor_entity, actor_kind, selection_operation
from .point_selection_state import PointSelectionState
from .pyvista_geometry import set_actor_selected
from opencae.model.selection import SelectableKind, SelectionOperation, ViewportSelection


class PyVistaPicker:
    def __init__(self, owner):
        self.owner = owner; self.selected_actors = set(); self.selected_cells = set()
        self.points = PointSelectionState(owner); self.elements = ElementSelectionState(owner)
    def enable(self): self.configure()
    def configure(self):
        try: self.owner.plotter.disable_picking()
        except Exception as exc: self.owner.message.emit(f"Could not reset viewport picker: {exc}")
        mode = self.owner.selection_mode
        if self.owner.stage == "RESULTS" or not self.owner.context_pick.active or mode == "none":
            self.update_pickability(); return
        try:
            if mode == "point":
                self.owner.plotter.enable_point_picking(callback=self.points.picked, left_clicking=True, show_message=False, show_point=False, picker="point", pickable_window=False)
            elif mode == "element" or (mode == "auto" and self.owner.display_mode == "mesh"):
                self.owner.plotter.enable_surface_point_picking(callback=self.elements.picked, left_clicking=True, show_message=False, show_point=False, picker="cell", pickable_window=False)
            else:
                self.owner.plotter.enable_mesh_picking(callback=self.picked_actor, use_actor=True, show=False, show_message=False, picker="hardware", left_clicking=True)
        except Exception as exc:
            self.owner.message.emit(f"Could not configure {mode} picking: {exc}")
        self.update_pickability()
    def clear(self, emit=True, render=True):
        for actor in tuple(self.selected_actors): set_actor_selected(actor, False, actor_kind(self.owner.scene, actor))
        self.selected_actors.clear(); self.selected_cells.clear(); self.points.clear(); self.elements.clear()
        preview = getattr(self.owner.scene, "selection_preview_overlay", None)
        if preview is not None:
            preview.reapply_actor_styles()
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
        operation = selection_operation()
        hit = actor_entity(scene, actor)
        if hit is None: return
        if operation == SelectionOperation.REPLACE:
            self.clear(False, False)
            self.selected_actors.add(actor); set_actor_selected(actor, True, kind)
        elif operation == SelectionOperation.REMOVE:
            self.selected_actors.discard(actor); set_actor_selected(actor, False, kind)
        else:
            self.selected_actors.add(actor); set_actor_selected(actor, True, kind)
        self.emit_entities(
            [item for item in (actor_entity(scene, current) for current in self.selected_actors) if item],
            [hit.with_operation(operation)],
        )
    def emit_entities(self, entities, event_entities=None):
        if self.owner.handle_entities(event_entities or entities): self.clear(False, False)
        else:
            self.owner.selection_changed.emit(ViewportSelection.from_hits(entities) if entities else None)
        self.owner.plotter.render()
    def show_labels(self, values, render=True):
        from opencae.model.selection import RegionDefinition, selection_item_label
        project = self.owner.store.project
        definition = RegionDefinition.from_values(values)
        self.clear(False, False)
        wanted = {selection_item_label(project, item) for item in definition.items}
        actors = (*self.owner.scene.face_actors, *self.owner.scene.edge_actors, *self.owner.scene.vertex_actors, *self.owner.scene.reference_actors, *self.owner.scene.datum_actors)
        for actor in actors:
            entity = actor_entity(self.owner.scene, actor)
            if entity and entity.label in wanted:
                self.selected_actors.add(actor); set_actor_selected(actor, True, actor_kind(self.owner.scene, actor))
        if render: self.owner.plotter.render()
    def update_pickability(self):
        mode = self.owner.selection_mode; scene = self.owner.scene
        context = self.owner.context_pick
        active = context.active and self.owner.stage != "RESULTS" and mode != "none"
        if active:
            kinds = context.policy.accepted_kinds
            for actor in scene.face_actors: actor.SetPickable(SelectableKind.GEOMETRY_FACE in kinds or SelectableKind.GEOMETRY_CELL in kinds)
            for actor in scene.edge_actors: actor.SetPickable(SelectableKind.GEOMETRY_EDGE in kinds)
            for actor in scene.vertex_actors:
                actor.SetPickable(SelectableKind.GEOMETRY_VERTEX in kinds); actor.SetVisibility(self.owner.display_mode == "geometry")
            for actor in scene.reference_actors: actor.SetPickable(SelectableKind.REFERENCE_POINT in kinds)
            for actor in scene.datum_actors: actor.SetPickable(False)
            mesh_pickable = self.owner.display_mode == "mesh" and bool(kinds & {SelectableKind.MESH_NODE, SelectableKind.MESH_ELEMENT, SelectableKind.MESH_FACET})
            if scene.mesh_actor is not None: scene.mesh_actor.SetPickable(mesh_pickable)
            for actor in scene.mesh_actors: actor.SetPickable(mesh_pickable)
            return
        # No free-form viewport selection exists outside a dialog-owned
        # context session. Geometry remains visible, but every actor is inert.
        for actor in scene.face_actors: actor.SetPickable(False)
        for actor in scene.edge_actors: actor.SetPickable(False)
        for actor in scene.vertex_actors:
            actor.SetPickable(False); actor.SetVisibility(False)
        for actor in scene.reference_actors: actor.SetPickable(False)
        for actor in scene.datum_actors: actor.SetPickable(False)
        if scene.mesh_actor is not None: scene.mesh_actor.SetPickable(False)
        for actor in scene.mesh_actors: actor.SetPickable(False)
