"""Coordinates mesh generation, clearing, and element-definition editing."""

from copy import deepcopy

from opencae.geometry.element_controls_apply import apply_all_controls
from opencae.geometry.errors import GeometryError
from opencae.model.mesh import create_element_definition
from opencae.ui.dialogs.edit_elements import EditElementsDialog

from .mesh_persistence import apply_mesh_snapshot
from ..busy import busy_cursor
from ..dialog_runner import get_values


class PartMeshGeneration:
    """Controller flow for persistent mesh state on the active Part."""

    def __init__(self, context):
        """Bind the shared Part-controller context."""
        self.ctx = context

    def generate_mesh(self):
        """Generate a mesh candidate and atomically replace the active Part."""
        part = self.ctx.active_part()
        if not self.ctx.require_geometry(part):
            return
        if not part.mesh.seeds:
            self.ctx.store.message.emit(
                "Create a part or edge seed before meshing"
            )
            return
        candidate = deepcopy(part)
        try:
            with busy_cursor():
                snapshot = self.ctx.service.generate_mesh(candidate)
        except GeometryError as exc:
            self.ctx.error("Mesh generation failed", exc)
            return

        apply_mesh_snapshot(candidate, snapshot)
        apply_all_controls(candidate)
        self.ctx.service.invalidate(candidate.id, mesh_only=True)
        self.ctx.replace_part(
            candidate,
            f"Generated mesh for {part.name}",
        )
        if snapshot.seed_mismatches:
            details = ", ".join(
                f"{name}: expected {values[0]}, got {values[1]}"
                for name, values in snapshot.seed_mismatches.items()
            )
            self.ctx.store.message.emit(
                f"Gmsh did not preserve all edge seeds ({details})"
            )
        if hasattr(self.ctx.parent, "viewport"):
            self.ctx.parent.viewport.set_display_mode("mesh")

    def clear_mesh(self):
        """Remove generated mesh data while retaining meshing configuration."""
        part = self.ctx.active_part()
        if part is None:
            return
        candidate = deepcopy(part)
        candidate.mesh.node_count = 0
        candidate.mesh.element_count = 0
        candidate.mesh.mesh_dimension = 0
        candidate.mesh.minimum_quality = None
        candidate.mesh.mean_quality = None
        candidate.mesh.element_definitions.clear()
        candidate.mesh.nodes.ids.clear()
        candidate.mesh.nodes.coordinates.clear()
        candidate.mesh.element_blocks.clear()
        candidate.mesh.entity_nodes.clear()
        candidate.mesh.entity_elements.clear()
        candidate.mesh.entity_facets.clear()
        candidate.mesh.status = "Not generated"
        self.ctx.service.invalidate(part.id, mesh_only=True)
        self.ctx.replace_part(
            candidate,
            f"Cleared mesh for {part.name}",
        )

    def edit_elements(self):
        """Edit one canonical element definition selected by solver metadata."""
        values = get_values(EditElementsDialog(self.ctx.parent))
        part = self.ctx.active_part()
        if not values or part is None:
            return

        candidate = deepcopy(part)
        existing = next(
            (
                item
                for item in candidate.mesh.element_definitions
                if item.category == values["category"]
                and item.topology == values["topology"]
            ),
            None,
        )
        if existing is None:
            target = create_element_definition(
                values["category"],
                values["topology"],
                name=values["topology"],
            )
            candidate.mesh.element_definitions.append(target)
        else:
            target = existing

        target.order = values["order"]
        target.formulation = values["formulation"]
        target.count = values["count"] or target.count
        self.ctx.replace_part(
            candidate,
            f"Edited {values['topology']}",
        )
