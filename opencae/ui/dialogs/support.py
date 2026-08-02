from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QMessageBox, QVBoxLayout

from opencae.model.naming import is_unique
from opencae.ui.core.widgets import ComponentsWidget, ReferenceSelector


class SupportDialog(QDialog):
    def __init__(self, support_type, regions=(), coordinate_systems=(), create_region=None, parent=None, default_name="", existing_names=()):
        super().__init__(parent); self.support_type = support_type; self.existing_names = tuple(existing_names)
        self.setWindowTitle(f"Create {support_type}"); self.setMinimumWidth(600); root = QVBoxLayout(self); form = QFormLayout()
        self.name = QLineEdit(default_name or f"{support_type}-1"); self.region = ReferenceSelector(regions, regions[0] if regions else "", create_region)
        self.csys = ReferenceSelector(["Global", *coordinate_systems], "Global")
        form.addRow("Name", self.name); form.addRow("Region", self.region); form.addRow("Coordinate system", self.csys); root.addLayout(form)
        defaults = [0.0] * 6 if support_type == "Fixed" else [None] * 6
        self.components = ComponentsWidget(("Ux", "Uy", "Uz", "Rx", "Ry", "Rz"), defaults, checkable=True, editable=support_type != "Fixed"); root.addWidget(self.components)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept); buttons.rejected.connect(self.reject); root.addWidget(buttons)

    def _accept(self):
        name = self.name.text().strip()
        if not is_unique(name, self.existing_names): QMessageBox.warning(self, "Duplicate name", f"A support named '{name}' already exists."); return
        self.accept()

    def values(self):
        return {"name": self.name.text().strip(), "region_name": self.region.currentText(), "coordinate_system": self.csys.currentText(), "components": self.components.values()}
