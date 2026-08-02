from copy import deepcopy

from opencae.geometry.errors import GeometryError
from opencae.model.mesh import create_element_definition
from .mesh_persistence import apply_mesh_snapshot
from opencae.geometry.element_controls_apply import apply_all_controls
from opencae.ui.dialogs.edit_elements import EditElementsDialog

from ..busy import busy_cursor
from ..dialog_runner import get_values


class PartMeshGeneration:
    def __init__(self, context):
        self.ctx = context

    def generate_mesh(self):
        part = self.ctx.active_part()
        if not self.ctx.require_geometry(part):
            return
        if not part.mesh.seeds:
            self.ctx.store.message.emit("Create a part or edge seed before meshing")
            return
        candidate = deepcopy(part)
        try:
            with busy_cursor():
                snapshot, definitions = self.ctx.service.generate_mesh(candidate)
        except GeometryError as exc:
            self.ctx.error("Mesh generation failed", exc)
            return
        apply_mesh_snapshot(candidate, snapshot, definitions)
        apply_all_controls(candidate)
        self.ctx.service.invalidate(candidate.id, mesh_only=True)
        self.ctx.replace_part(candidate, f"Generated mesh for {part.name}")
        if snapshot.seed_mismatches:
            details = ", ".join(f"{name}: expected {values[0]}, got {values[1]}" for name, values in snapshot.seed_mismatches.items())
            self.ctx.store.message.emit(f"Gmsh did not preserve all edge seeds ({details})")
        if hasattr(self.ctx.parent, "viewport"):
            self.ctx.parent.viewport.set_display_mode("mesh")

    def clear_mesh(self):
        part = self.ctx.active_part()
        if part is None:
            return
        def clear(_project):
            part.mesh.node_count = part.mesh.element_count = part.mesh.mesh_dimension = 0
            part.mesh.minimum_quality = part.mesh.mean_quality = None
            part.mesh.elements.clear(); part.mesh.nodes.ids.clear(); part.mesh.nodes.coordinates.clear(); part.mesh.element_blocks.clear()
            part.mesh.entity_nodes.clear(); part.mesh.entity_elements.clear()
            part.mesh.status = "Not generated"
        self.ctx.store.mutate(f"Cleared mesh for {part.name}", clear)
        self.ctx.service.invalidate(part.id, mesh_only=True)
        self.ctx.store.invalidate_scene(f"Cleared mesh for {part.name}")

    def edit_elements(self):
        values = get_values(EditElementsDialog(self.ctx.parent))
        part = self.ctx.active_part()
        if not values or part is None:
            return
        existing = next(
            (
                item for item in part.mesh.elements
                if item.category == values["category"] and item.topology == values["topology"]
            ),
            None,
        )

        def update(_project):
            if existing is None:
                target = create_element_definition(
                    values["category"],
                    values["topology"],
                    name=values["topology"],
                )
                part.mesh.elements.append(target)
            else:
                target = existing
            target.order = values["order"]
            target.formulation = values["formulation"]
            target.count = values["count"] or target.count

        self.ctx.store.mutate(f"Edited {values['topology']}", update)
