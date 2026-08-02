from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QMessageBox, QVBoxLayout

from opencae.model.naming import is_unique
from opencae.ui.core.widgets import ReferenceSelector


class BaseLoadDialog(QDialog):
    def __init__(self, title, regions=(), coordinate_systems=(), create_region=None, show_region=True, show_csys=True, parent=None, default_name="", existing_names=()):
        super().__init__(parent)
        self.existing_names = tuple(existing_names)
        self.setWindowTitle(f"Create {title}")
        self.setMinimumWidth(620)
        self.root = QVBoxLayout(self); self.form = QFormLayout()
        self.name = QLineEdit(default_name or f"{title}-1"); self.form.addRow("Name", self.name)
        self.region = None
        if show_region:
            self.region = ReferenceSelector(regions, regions[0] if regions else "", create_region)
            self.form.addRow("Region", self.region)
        self.csys = None
        if show_csys:
            self.csys = ReferenceSelector(["Global", *coordinate_systems], "Global")
            self.form.addRow("Coordinate system", self.csys)
        self.root.addLayout(self.form)

    def finish(self):
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept); buttons.rejected.connect(self.reject); self.root.addWidget(buttons)


    def _accept(self):
        name = self.name.text().strip()
        if not is_unique(name, self.existing_names): QMessageBox.warning(self, "Duplicate name", f"A load named '{name}' already exists."); return
        self.accept()

    def common_values(self):
        values = {"name": self.name.text().strip()}
        if self.region is not None: values["region_name"] = self.region.currentText()
        if self.csys is not None: values["coordinate_system"] = self.csys.currentText()
        return values
