from PyQt6.QtWidgets import QDialog, QLabel, QLineEdit, QMessageBox, QVBoxLayout

from opencae.ui.core.controls import dialog_buttons
from .material_behavior_row import MaterialBehaviorRow
from .material_property import MaterialPropertyDialog

_CATEGORIES = ("Elasticity", "Density", "Plasticity", "Thermal expansion")


class MaterialDialog(QDialog):
    def __init__(self, material=None, existing_names=(), parent=None, default_name="Material-1"):
        super().__init__(parent); self.material = material; self.existing_names = {name.casefold() for name in existing_names}
        self.behaviors = list(getattr(material, "behaviors", [])); self.rows = {}
        self.setWindowTitle("Edit Material" if material else "Create Material"); self.setMinimumSize(650, 470)
        root = QVBoxLayout(self); root.setContentsMargins(18, 16, 18, 14); root.setSpacing(10)
        title = QLabel(self.windowTitle()); title.setObjectName("PanelTitle"); root.addWidget(title)
        root.addWidget(QLabel("Name")); self.name = QLineEdit(material.name if material else default_name); root.addWidget(self.name)
        root.addWidget(QLabel("Material definitions"))
        for category in _CATEGORIES:
            row = MaterialBehaviorRow(category); row.add_requested.connect(self._edit_category); row.remove_requested.connect(self._remove_category)
            root.addWidget(row); self.rows[category] = row
        root.addStretch(1)
        buttons = dialog_buttons(); buttons.accepted.connect(self._accept); buttons.rejected.connect(self.reject); root.addWidget(buttons)
        self._refresh()

    def _behavior(self, category): return next((item for item in self.behaviors if item.category == category), None)

    def _refresh(self):
        for category, row in self.rows.items(): row.set_behavior(self._behavior(category))

    def _edit_category(self, category):
        current = self._behavior(category); dialog = MaterialPropertyDialog(current, self, category)
        if dialog.exec() != QDialog.DialogCode.Accepted: return
        value = dialog.behavior_value(); self.behaviors = [item for item in self.behaviors if item.category != category]
        self.behaviors.append(value); self._refresh()

    def _remove_category(self, category):
        self.behaviors = [item for item in self.behaviors if item.category != category]; self._refresh()

    def _accept(self):
        name = self.name.text().strip()
        if not name: QMessageBox.warning(self, "Invalid material", "Enter a material name."); return
        if name.casefold() in self.existing_names and (self.material is None or name.casefold() != self.material.name.casefold()):
            QMessageBox.warning(self, "Duplicate name", f"A material named '{name}' already exists."); return
        self.accept()

    def values(self):
        return {"name": self.name.text().strip(), "behaviors": self.behaviors, "fields": [],
                "properties": dict(getattr(self.material, "properties", {})), "density": 0.0,
                "youngs_modulus": 0.0, "poisson_ratio": 0.0}
