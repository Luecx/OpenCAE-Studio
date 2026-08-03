from __future__ import annotations

from copy import deepcopy

from PyQt6.QtWidgets import QMessageBox

from opencae.geometry.element_control_summary import preview, summarize
from opencae.geometry.element_controls_apply import apply_control
from opencae.geometry.section_compatibility import incompatible_assignments
from opencae.model.entities.mesh import ElementControl
from opencae.model.naming import next_name
from opencae.model.selection import (
    RegionProjection,
    RegionRequirement,
    SelectableKind,
    SelectionPolicy,
    definition_from_local_labels,
)
from opencae.ui.dialogs.element_control import ElementControlDialog
from ..element_control_session import ElementControlSession
from ..region_selection import begin_region_pick, region_options


class PartElementControls:
    def __init__(self, context):
        self.ctx = context
        self.dialogs = []
        self.session = ElementControlSession(context.store, context.parent, self.dialogs)

    def element_controls(self):
        self._open(None)

    def edit_element_control(self, control):
        self._open(control)

    def _open(self, control):
        part = self.ctx.active_part()
        if part is None or not part.mesh.element_blocks:
            self.ctx.store.message.emit("Generate or import a mesh before editing element controls")
            return

        requirement = RegionRequirement(RegionProjection.ELEMENTS, (1, 2, 3), 1)
        policy = SelectionPolicy.create(
            {
                SelectableKind.GEOMETRY_EDGE,
                SelectableKind.GEOMETRY_FACE,
                SelectableKind.GEOMETRY_CELL,
                SelectableKind.MESH_ELEMENT,
            },
            multiple=True,
            requirement=requirement,
        )

        def pick(_owner, done, finished):
            return begin_region_pick(
                self.ctx.store.project,
                self.ctx.parent.viewport,
                policy,
                done,
                default_owner=part,
                finished=finished,
            )

        initial = definition_from_local_labels(part, self.ctx.selected_labels())
        dialog = ElementControlDialog(
            self.ctx.store.project,
            lambda target: summarize(self.ctx.store.project.resolve(part.id), target),
            lambda target, topology: preview(self.ctx.store.project.resolve(part.id), target, topology),
            options=region_options(
                self.ctx.store.project,
                owner=part,
                include_reference_points=False,
                projections=(RegionProjection.ELEMENTS,),
            ),
            pick_region=pick,
            control=control,
            initial=initial,
            parent=self.ctx.parent,
        )
        holder = {"id": control.id if control else None}
        self.session.open(dialog, lambda values: self._commit(part.id, holder, values))

    def _commit(self, part_id, holder, values):
        part = self.ctx.store.project.try_resolve(part_id)
        if part is None:
            self.ctx.store.message.emit("The edited part no longer exists")
            return
        candidate = deepcopy(part)
        control = next(
            (item for item in candidate.mesh.element_controls if item.id == holder["id"]),
            None,
        )
        if control is None:
            control = ElementControl(
                name=next_name("Element Control", candidate.mesh.element_controls)
            )
            candidate.mesh.element_controls.append(control)
            holder["id"] = control.id
        control.target = values["target"]
        control.topology = values["topology"]
        control.order = values["order"]
        control.formulation = values["formulation"]

        state = preview(candidate, control.target, control.topology)
        family = (
            control.formulation
            if control.topology.value == "line" and control.formulation != "Keep Existing"
            else ""
        )
        conflicts = incompatible_assignments(
            self.ctx.store.project, candidate, state.selected, family
        )
        if conflicts:
            QMessageBox.warning(
                self.ctx.parent,
                "Incompatible section",
                "The element family conflicts with assigned sections:\n\n" + "\n".join(conflicts),
            )
            return
        selected, affected = apply_control(candidate, control)
        if not selected:
            QMessageBox.warning(
                self.ctx.parent,
                "Element Controls",
                "The target contains no elements of the selected topology.",
            )
            return
        self.ctx.service.invalidate(candidate.id, mesh_only=True)
        self.ctx.replace_part(
            candidate,
            f"Applied {control.name} to {len(selected):,} elements ({len(affected):,} affected)",
        )
