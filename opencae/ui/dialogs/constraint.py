from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QDoubleSpinBox, QFormLayout, QLineEdit, QMessageBox, QVBoxLayout

from opencae.model.entities.constraints import ConstraintType, constraint_region_requirement, direct_control_point_error
from opencae.model.naming import is_unique
from opencae.model.selection import RegionDefinition
from opencae.ui.core.apply_dialog import ApplyDialog
from opencae.ui.core.controls import dialog_buttons
from opencae.ui.core.unit_context import unit_system_for
from opencae.ui.core.widgets import ChevronComboBox, CompactRegionSelector


class ConstraintDialog(ApplyDialog):
    preview_changed = pyqtSignal(object, object)
    def __init__(self, project, options=(), pick_callback=None, save_callback=None, parent=None,
                 default_name="Constraint-1", existing_names=(), initial_type=ConstraintType.KINEMATIC,
                 constraint=None, validator=None):
        super().__init__(parent)
        self.project = project; self.existing_names = tuple(existing_names); self.constraint = constraint; self.validator = validator
        self.pick_callback = pick_callback; self.save_callback = save_callback
        self.setWindowTitle("Edit Constraint" if constraint else "Create Constraint"); self.setMinimumWidth(760)
        root = QVBoxLayout(self); form = QFormLayout(); self.form = form
        self.name = QLineEdit(getattr(constraint, "name", default_name))
        self.kind = ChevronComboBox()
        for value in ConstraintType: self.kind.addItem(value.value, value.value)
        current_kind = str(getattr(constraint, "constraint_type", initial_type)); self.kind.setCurrentIndex(max(0, self.kind.findData(current_kind)))
        master = _master_definition(constraint); slave = _slave_definition(constraint)
        self.master = CompactRegionSelector(
            project, master, options,
            lambda owner, done, finished: self._pick("master", owner, done, finished),
            lambda owner, definition: self._save("master", owner, definition),
        )
        self.slave = CompactRegionSelector(
            project, slave, options,
            lambda owner, done, finished: self._pick("slave", owner, done, finished),
            lambda owner, definition: self._save("slave", owner, definition),
        )
        form.addRow("Name", self.name); form.addRow("Type", self.kind); form.addRow("Master / control", self.master); form.addRow("Slave / body", self.slave)
        components = tuple(getattr(constraint, "components", (1, 1, 1, 1, 1, 1)))
        self.components = []
        for label, value in zip(("U1", "U2", "U3", "R1", "R2", "R3"), components):
            box = QCheckBox(); box.setChecked(bool(value)); self.components.append(box); form.addRow(label, box)
        self.adjust = QCheckBox(); self.adjust.setChecked(bool(getattr(constraint, "adjust", False)))
        self.distance = QDoubleSpinBox(); self.distance.setRange(0.0, 1e300); self.distance.setDecimals(12); self.distance.setValue(float(getattr(constraint, "distance", 0.0) or 0.0)); self.distance.setSuffix(f" {unit_system_for(self).symbol('length')}")
        form.addRow("Adjust tie", self.adjust); form.addRow("Tie distance", self.distance)
        root.addLayout(form); buttons = dialog_buttons(include_apply=True); self.bind_buttons(buttons, True); root.addWidget(buttons)
        self.kind.currentIndexChanged.connect(self._update_type)
        self.master.value_changed.connect(lambda _value: self._emit_preview())
        self.slave.value_changed.connect(lambda _value: self._emit_preview())
        self._update_type()

    def _pick(self, role, owner, done, finished):
        return self.pick_callback(self.constraint_type(), role, owner, done, finished) if self.pick_callback else None

    def _save(self, role, owner, definition):
        if self.save_callback: return self.save_callback(self.constraint_type(), role, owner, definition)

    def constraint_type(self): return ConstraintType.coerce(self.kind.currentData())

    def _update_type(self):
        self.master.finish_pick(); self.slave.finish_pick()
        kind = self.constraint_type(); tie = kind == ConstraintType.TIE; coupling = kind in {ConstraintType.KINEMATIC, ConstraintType.DISTRIBUTING}
        self.master.set_requirement(constraint_region_requirement(kind, "master"))
        self.slave.set_requirement(constraint_region_requirement(kind, "slave"))
        master_label, slave_label = {
            ConstraintType.KINEMATIC: ("Control point", "Coupled region"),
            ConstraintType.DISTRIBUTING: ("Control point", "Distributed region"),
            ConstraintType.TIE: ("Master surface", "Slave surface"),
            ConstraintType.RIGID_BODY: ("Reference point", "Rigid body region"),
        }.get(kind, ("Master", "Slave"))
        self.form.labelForField(self.master).setText(master_label)
        self.form.labelForField(self.slave).setText(slave_label)
        self.form.labelForField(self.adjust).setVisible(tie); self.adjust.setVisible(tie)
        self.form.labelForField(self.distance).setVisible(tie); self.distance.setVisible(tie)
        self.master.set_extended_visible(tie)
        self.slave.set_extended_visible(True)
        if (coupling or kind == ConstraintType.RIGID_BODY) and not self.master.definition().empty:
            if direct_control_point_error(self.master.definition()):
                self.master.clear()
        for component in self.components:
            component.setVisible(coupling)
            label = self.form.labelForField(component)
            if label: label.setVisible(coupling)
        self._emit_preview()

    def _emit_preview(self):
        self.preview_changed.emit(self.master.definition(), self.slave.definition())

    def preview_definitions(self):
        return self.master.definition(), self.slave.definition()

    def values(self):
        kind = self.constraint_type()
        values = {"name": self.name.text().strip(), "constraint_type": kind}
        if kind in {ConstraintType.KINEMATIC, ConstraintType.DISTRIBUTING}:
            values.update(control_point=self.master.definition(), slave=self.slave.definition(), components=tuple(int(item.isChecked()) for item in self.components))
        elif kind == ConstraintType.TIE:
            values.update(master=self.master.definition(), slave=self.slave.definition(), adjust=self.adjust.isChecked(), distance=self.distance.value())
        elif kind == ConstraintType.RIGID_BODY:
            values.update(reference=self.master.definition(), body=self.slave.definition())
        else:
            values.update(master=self.master.definition(), slave=self.slave.definition())
        return values

    def validate(self):
        allowed = [item for item in self.existing_names if not self.constraint or item.casefold() != self.constraint.name.casefold()]
        if not is_unique(self.name.text().strip(), allowed):
            QMessageBox.warning(self, "Duplicate name", f"A constraint named '{self.name.text().strip()}' already exists."); return False
        if self.master.definition().empty or self.slave.definition().empty:
            QMessageBox.warning(self, "Missing target", "Select both master/control and slave/body regions."); return False
        if self.validator:
            error = self.validator(self.values())
            if error: QMessageBox.warning(self, "Invalid constraint regions", error); return False
        return True

    def prepare_new(self, default_name, existing_names):
        self.constraint = None; self.existing_names = tuple(existing_names); self.name.setText(default_name); self.master.clear(); self.slave.clear()


def _master_definition(constraint):
    if constraint is None: return RegionDefinition()
    return getattr(constraint, "control_point", getattr(constraint, "reference", getattr(constraint, "master", RegionDefinition())))


def _slave_definition(constraint):
    if constraint is None: return RegionDefinition()
    return getattr(constraint, "body", getattr(constraint, "slave", RegionDefinition()))
