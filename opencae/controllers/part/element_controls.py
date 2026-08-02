from copy import deepcopy

from PyQt6.QtWidgets import QMessageBox

from opencae.geometry.element_control_summary import preview, summarize
from opencae.geometry.element_controls_apply import apply_control
from opencae.geometry.section_compatibility import incompatible_assignments
from opencae.model.entities.mesh import ElementControl
from opencae.model.naming import next_name
from opencae.ui.dialogs.element_control import ElementControlDialog
from ..element_control_session import ElementControlSession


class PartElementControls:
    def __init__(self, context):
        self.ctx = context; self.dialogs = []; self.session = ElementControlSession(context.store, context.parent, self.dialogs)

    def element_controls(self): self._open(None)
    def edit_element_control(self, control): self._open(control)

    def _open(self, control):
        part = self.ctx.active_part()
        if part is None or not part.mesh.element_blocks:
            self.ctx.store.message.emit("Generate or import a mesh before editing element controls"); return
        dialog = ElementControlDialog(
            lambda targets: summarize(self.ctx.active_part(), targets),
            lambda targets, topology: preview(self.ctx.active_part(), targets, topology),
            lambda: self.ctx.selected_labels(), part.element_sets,
            control=control, initial=self.ctx.selected_labels(), parent=self.ctx.parent,
        )
        holder = {"id": control.id if control else None}
        self.session.open(dialog, lambda values: self._commit(holder, values))

    def _commit(self, holder, values):
        part = self.ctx.active_part(); candidate = deepcopy(part)
        control = next((item for item in candidate.mesh.element_controls if item.id == holder["id"]), None)
        target_key = tuple(sorted(map(str, values["targets"])))
        if control is None:
            control = next((item for item in candidate.mesh.element_controls if tuple(sorted(map(str, item.targets))) == target_key and item.topology == values["topology"]), None)
        if control is None:
            control = ElementControl(name=next_name("Element Control", candidate.mesh.element_controls)); candidate.mesh.element_controls.append(control); holder["id"] = control.id
        else:
            holder["id"] = control.id; candidate.mesh.element_controls.remove(control); candidate.mesh.element_controls.append(control)
        control.targets = list(values["targets"]); control.topology = values["topology"]
        control.order = values["order"]; control.formulation = values["formulation"]
        state = preview(candidate, control.targets, control.topology)
        family = control.formulation if control.topology.value == "line" and control.formulation != "Keep Existing" else ""
        conflicts = incompatible_assignments(self.ctx.store.project, candidate, state.selected, family)
        if conflicts:
            QMessageBox.warning(self.ctx.parent, "Incompatible section", "The element family conflicts with assigned sections:\n\n" + "\n".join(conflicts)); return
        selected, affected = apply_control(candidate, control)
        if not selected:
            QMessageBox.warning(self.ctx.parent, "Element Controls", "The target contains no elements of the selected topology."); return
        self.ctx.service.invalidate(candidate.id, mesh_only=True)
        self.ctx.replace_part(candidate, f"Applied {control.name} to {len(selected):,} elements ({len(affected):,} affected)")
