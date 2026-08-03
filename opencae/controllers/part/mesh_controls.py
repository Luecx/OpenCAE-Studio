from __future__ import annotations

from copy import deepcopy

from opencae.model.mesh import create_mesh_control
from opencae.model.selection import (
    RegionProjection, RegionRequirement, SelectableKind, SelectionPolicy,
    definition_from_local_labels, local_geometry_tags, region_definition_error,
)
from opencae.store.commands import CompositeCommand, UpdateFieldCommand, make_add_command, make_replace_command
from opencae.ui.dialogs.mesh_control import MeshControlDialog
from opencae.ui.dialogs.mesh_settings import MeshSettingsDialog
from ..dialog_runner import get_values
from ..region_selection import begin_region_pick, region_options


class PartMeshControls:
    def __init__(self, context): self.ctx = context

    def mesh_control(self):
        part = self.ctx.active_part()
        if not self.ctx.require_geometry(part): return
        initial = definition_from_local_labels(part, self.ctx.selected_labels())
        values = get_values(self._dialog(part, definition=initial))
        if not values: return
        self._commit(part.id, values)

    def edit_mesh_control(self, control):
        part = self.ctx.active_part()
        values = get_values(self._dialog(part, control=control)) if part else None
        if not values: return
        self._commit(part.id, values, control.id)

    def _dialog(self, part, definition=None, control=None):
        def pick(scope, _owner, done, finished):
            dimension = {"Edge": 1, "Face": 2, "Cell": 3}[scope]
            kind = {1: SelectableKind.GEOMETRY_EDGE, 2: SelectableKind.GEOMETRY_FACE, 3: SelectableKind.GEOMETRY_CELL}[dimension]
            policy = SelectionPolicy.create(
                {kind}, multiple=True,
                requirement=RegionRequirement(RegionProjection.ELEMENTS, (dimension,), 0),
            )
            return begin_region_pick(self.ctx.store.project, self.ctx.parent.viewport, policy, done, default_owner=part, finished=finished)

        dialog = MeshControlDialog(
            self.ctx.store.project,
            options=region_options(
                self.ctx.store.project, owner=part, include_reference_points=False,
                projections=(RegionProjection.ELEMENTS,),
            ),
            definition=definition or getattr(control, "target", None),
            pick_callback=pick,
            control=control,
            parent=self.ctx.parent,
        )
        preview_channel = f"mesh-control-dialog-{id(dialog)}"

        def requirement(scope):
            dimension = {"Edge": 1, "Face": 2, "Cell": 3}[scope]
            return RegionRequirement(RegionProjection.ELEMENTS, (dimension,), 0)

        def preview(value):
            self.ctx.parent.viewport.show_region_preview(
                preview_channel, value, color="#3296e6",
                opacity=.62, point_size=16, show_point_labels=False,
            )

        dialog.target.set_requirement(requirement(dialog.scope.currentText()), allow_part_local=True)
        dialog.scope.currentTextChanged.connect(
            lambda value: dialog.target.set_requirement(requirement(value), allow_part_local=True)
        )
        dialog.target.value_changed.connect(preview)
        def finish(_code):
            self.ctx.parent.viewport.cancel_context_pick()
            self.ctx.parent.viewport.clear_region_preview(preview_channel)

        dialog.finished.connect(finish)
        preview(dialog.target.definition())
        return dialog

    def _commit(self, part_id, values, control_id=None):
        part = self.ctx.store.project.try_resolve(part_id)
        if part is None: return
        dimension = {"Edge": 1, "Face": 2, "Cell": 3}[values["scope"]]
        target = values["target"]
        requirement = RegionRequirement(RegionProjection.ELEMENTS, (dimension,), 0)
        error = region_definition_error(
            self.ctx.store.project, target, requirement, allow_part_local=True
        )
        if error:
            self.ctx.store.message.emit(error)
            return
        current = self.ctx.store.project.try_resolve(control_id) if control_id else None
        replacement = create_mesh_control(
            values["technique"], id=current.id if current else None,
            name=values["name"], scope=values["scope"], topology=values["topology"], target=target,
        ) if current else create_mesh_control(
            values["technique"], name=values["name"], scope=values["scope"],
            topology=values["topology"], target=target,
        )
        mutation = make_replace_command(self.ctx.store.project, part_id, "mesh.controls", replacement) if current else make_add_command(self.ctx.store.project, part_id, "mesh.controls", replacement)
        command = CompositeCommand((mutation, UpdateFieldCommand(part_id, "mesh.status", part.mesh.status, "Outdated")))
        self.ctx.store.execute(f"{'Edited' if current else 'Created'} {replacement.name}", command)
        self.ctx.service.invalidate(part_id, mesh_only=True)

    def mesh_settings(self):
        part = self.ctx.active_part()
        if part is None:
            self.ctx.store.message.emit("Create or import a part first")
            return
        values = get_values(MeshSettingsDialog(part.mesh.settings, self.ctx.parent))
        if not values: return
        candidate = deepcopy(part.mesh.settings)
        for key, value in values.items(): setattr(candidate, key, value)
        commands = [UpdateFieldCommand(part.id, "mesh.settings", part.mesh.settings, candidate)]
        if part.mesh.status != "Outdated": commands.append(UpdateFieldCommand(part.id, "mesh.status", part.mesh.status, "Outdated"))
        self.ctx.store.execute("Updated Gmsh mesh settings", CompositeCommand(tuple(commands)))
        self.ctx.service.invalidate(part.id, mesh_only=True)
