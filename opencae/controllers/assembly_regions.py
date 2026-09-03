from __future__ import annotations

from opencae.ui.core.dialog_lifecycle import show_modeless_dialog
from opencae.ui.core.theme import PALETTE
from opencae.model.naming import next_name
from opencae.model.regions import create_region
from opencae.model.selection import RegionProjection, region_definition_error
from opencae.ui.dialogs.element_set import ElementSetDialog
from opencae.ui.dialogs.node_set import NodeSetDialog
from opencae.ui.dialogs.surface import SurfaceDialog
from .region_selection import begin_region_pick, policy_for_projection, region_options


class AssemblyRegions:
    def __init__(self, controller):
        self.controller = controller
        self.store = controller.store
        self.parent = controller.parent
        self.dialogs = []

    def node_set(self): self._open(RegionProjection.NODES)
    def element_set(self): self._open(RegionProjection.ELEMENTS)
    def surface(self): self._open(RegionProjection.FACETS)

    def edit(self, region):
        self._open(region.preferred_projection, region)
        return True

    def _open(self, projection, region=None):
        project = self.store.project
        projection = RegionProjection(projection)
        dialog_cls, prefix = {
            RegionProjection.NODES: (NodeSetDialog, "NODE_REGION"),
            RegionProjection.ELEMENTS: (ElementSetDialog, "ELEMENT_REGION"),
            RegionProjection.FACETS: (SurfaceDialog, "SURFACE_REGION"),
        }[projection]
        policy = policy_for_projection(projection)
        options = [(label, value) for label, value in region_options(project, projections=(projection,)) if not region or not any(item.operand.region_ref.entity_id == region.id for item in value.items if hasattr(item.operand, "region_ref"))]

        def pick(_owner, done, finished):
            return begin_region_pick(project, self.parent.viewport, policy, done, finished=finished)

        def validate(definition):
            return region_definition_error(project, definition, policy.requirement)

        dialog = dialog_cls(
            region=region,
            project=project,
            options=options,
            pick_callback=pick,
            validator=validate,
            default_name=next_name(prefix, project.assembly.regions),
            existing_names=[item.name for item in project.assembly.regions],
            parent=self.parent,
        )
        self.dialogs.append(dialog)
        existing_id = getattr(region, "id", None)

        def commit(values):
            payload = dict(values)
            if existing_id: payload["id"] = existing_id
            replacement = create_region("Region", scope="Assembly", preferred_projection=projection, **payload)
            description = f"{'Edited' if existing_id else 'Created'} assembly region {replacement.name}"
            if existing_id:
                self.store.replace_entity(description, project.assembly.id, "regions", replacement)
            else:
                self.store.add_entity(description, project.assembly.id, "regions", replacement)
            self.store.select(replacement)

        preview_channel = f"assembly-region-dialog-{id(dialog)}"

        def preview(definition):
            self.parent.viewport.suspend_model_selection_preview()
            self.parent.viewport.show_region_preview(
                preview_channel, definition, color=PALETTE["selection_3d"],
                opacity=.62, point_size=17, show_point_labels=True,
            )

        def finish(_code):
            self.parent.viewport.clear_region_preview(preview_channel)
            self.parent.viewport.restore_model_selection_preview()
            self._close(dialog)

        dialog.region.value_changed.connect(preview)
        dialog.committed.connect(commit)
        dialog.finished.connect(finish)
        show_modeless_dialog(dialog)
        dialog.begin_selection()
        preview(dialog.region.definition())

    def _close(self, dialog):
        if hasattr(self.parent, "viewport"):
            self.parent.viewport.cancel_context_pick()
        if dialog in self.dialogs:
            self.dialogs.remove(dialog)
