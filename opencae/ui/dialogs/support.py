from PyQt6.QtWidgets import QFormLayout, QLineEdit, QMessageBox, QVBoxLayout

from opencae.model.naming import is_unique
from opencae.model.selection import RegionDefinition
from opencae.ui.core.apply_dialog import ApplyDialog
from opencae.ui.core.controls import dialog_buttons
from opencae.ui.core.widgets import ComponentsWidget, ReferenceSelector, CompactRegionSelector


class SupportDialog(ApplyDialog):
    def __init__(self, support_type, project, regions=(), coordinate_systems=(), create_region=None, pick_region=None,
                 parent=None, default_name="", existing_names=(), support=None, target_validator=None, target_requirement=None):
        super().__init__(parent)
        self.support_type = support_type; self.support = support; self.existing_names = tuple(existing_names); self.target_validator = target_validator
        self.setWindowTitle(f"{'Edit' if support else 'Create'} {support_type}"); self.setMinimumWidth(720)
        root = QVBoxLayout(self); form = QFormLayout()
        self.name = QLineEdit(support.name if support else (default_name or f"{support_type}-1"))
        self.region = CompactRegionSelector(project, getattr(support, "target", RegionDefinition()), regions, pick_region, create_region, requirement=target_requirement)
        csys = support.coordinate_system_ref.entity_id if support and support.coordinate_system_ref else None
        self.csys = ReferenceSelector((("Global", None), *coordinate_systems), csys)
        form.addRow("Name", self.name); form.addRow("Target region", self.region); form.addRow("Coordinate system", self.csys); root.addLayout(form)
        defaults = getattr(support, "components", ([0.0] * 6 if support_type == "Fixed" else [None] * 6))
        self.components = ComponentsWidget(("Ux", "Uy", "Uz", "Rx", "Ry", "Rz"), defaults, checkable=True, editable=support_type != "Fixed", parent=self, quantities=("length", "length", "length", None, None, None))
        root.addWidget(self.components); buttons = dialog_buttons(include_apply=True); self.bind_buttons(buttons, True); root.addWidget(buttons)

    def validate(self):
        name = self.name.text().strip()
        if not is_unique(name, self.existing_names, self.support.name if self.support else None):
            QMessageBox.warning(self, "Duplicate name", f"A support named '{name}' already exists."); return False
        definition = self.region.definition()
        if definition.empty:
            QMessageBox.warning(self, "Missing region", "Select at least one target operand."); return False
        if self.target_validator:
            error = self.target_validator(definition)
            if error: QMessageBox.warning(self, "Invalid target region", error); return False
        return True

    def values(self):
        return {"name": self.name.text().strip(), "target": self.region.definition(), "coordinate_system_id": self.csys.currentValue(), "components": self.components.values()}

    def prepare_new(self, default_name, existing_names):
        self.support = None; self.existing_names = tuple(existing_names); self.name.setText(default_name); self.region.clear()
