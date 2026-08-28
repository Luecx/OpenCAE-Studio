"""Coordinates mesh generation, clearing, and element-definition editing."""

from copy import deepcopy

from opencae.controllers.background_task import BackgroundTask
from opencae.geometry import GeometryService
from opencae.geometry.element_controls_apply import apply_all_controls
from opencae.geometry.fingerprint import part_fingerprint
from opencae.model.mesh import create_element_definition
from opencae.ui.dialogs.edit_elements import EditElementsDialog

from .mesh_persistence import apply_mesh_snapshot
from ..dialog_runner import get_values


class PartMeshGeneration:
    """Controller flow for persistent mesh state on the active Part."""

    def __init__(self, context):
        """Bind the shared Part-controller context."""
        self.ctx = context
        self._mesh_task: BackgroundTask | None = None
        self._mesh_generation_token = 0

    def generate_mesh(self):
        """Generate a mesh candidate off-thread and atomically replace the Part."""
        part = self.ctx.active_part()
        if not self.ctx.require_geometry(part):
            return
        if not part.mesh.seeds:
            self.ctx.store.message.emit(
                "Create a part or edge seed before meshing"
            )
            return
        if self._mesh_task is not None and self._mesh_task.isRunning():
            self.ctx.store.message.emit(
                f"Mesh generation for {part.name} is already running"
            )
            return

        candidate = deepcopy(part)
        source_fingerprint = part_fingerprint(part, include_mesh=True)
        self._mesh_generation_token += 1
        token = self._mesh_generation_token
        part_id = part.id
        part_name = part.name
        self.ctx.store.message.emit(f"Generating mesh for {part_name}…")

        task = BackgroundTask(
            lambda: _generate_mesh_candidate(candidate),
            on_result=lambda result: self._mesh_generated(
                result,
                part_id,
                part_name,
                source_fingerprint,
                token,
            ),
            on_error=lambda error: self._mesh_failed(error, part_name, token),
            parent=self.ctx.parent,
        )
        self._mesh_task = task
        task.start()

    def _mesh_generated(
        self,
        result,
        part_id,
        part_name,
        source_fingerprint,
        token,
    ) -> None:
        """Commit a worker result only if the source Part is still unchanged."""
        self._mesh_task = None
        if token != self._mesh_generation_token:
            return
        current = self.ctx.store.project.try_resolve(part_id)
        if current is None:
            self.ctx.store.message.emit(
                f"Discarded generated mesh for {part_name}; the Part no longer exists"
            )
            return
        if part_fingerprint(current, include_mesh=True) != source_fingerprint:
            self.ctx.store.message.emit(
                f"Discarded generated mesh for {part_name}; the Part changed while meshing"
            )
            return

        candidate, snapshot = result
        self.ctx.service.invalidate(candidate.id, mesh_only=True)
        self.ctx.replace_part(
            candidate,
            f"Generated mesh for {part_name}",
        )
        if snapshot.seed_mismatches:
            details = ", ".join(
                f"{name}: expected {values[0]}, got {values[1]}"
                for name, values in snapshot.seed_mismatches.items()
            )
            self.ctx.store.message.emit(
                f"Gmsh did not preserve all edge seeds ({details})"
            )
        else:
            self.ctx.store.message.emit(f"Generated mesh for {part_name}")
        if hasattr(self.ctx.parent, "viewport"):
            self.ctx.parent.viewport.set_display_mode("mesh")

    def _mesh_failed(self, error, part_name, token) -> None:
        self._mesh_task = None
        if token != self._mesh_generation_token:
            return
        self.ctx.error("Mesh generation failed", error)
        self.ctx.store.message.emit(f"Mesh generation failed for {part_name}")

    def clear_mesh(self):
        """Remove generated mesh data while retaining meshing configuration."""
        part = self.ctx.active_part()
        if part is None:
            return
        # Invalidate any still-running worker result. Gmsh itself is not killed
        # unsafely; when it finishes its stale token is simply discarded.
        self._mesh_generation_token += 1
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


def _generate_mesh_candidate(candidate):
    """Build and persist one local mesh candidate without touching live Qt state."""
    snapshot = GeometryService().generate_mesh(candidate)
    apply_mesh_snapshot(candidate, snapshot)
    apply_all_controls(candidate)
    return candidate, snapshot
