from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QLabel, QLineEdit, QSpinBox, QVBoxLayout,
)

from opencae.model.selection import RegionDefinition
from opencae.ui.core.unit_context import unit_system_for
from opencae.ui.core.widgets import CompactRegionSelector


class EdgeSeedDialog(QDialog):
    apply_requested = pyqtSignal(object)

    def __init__(self, project, options=(), definition=None, pick_callback=None, seed=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seed Edges")
        self.setModal(False)
        self.setMinimumWidth(650)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        root = QVBoxLayout(self); root.setContentsMargins(18, 16, 18, 14); root.setSpacing(12)
        title = QLabel("Seed Edges"); title.setObjectName("PanelTitle"); root.addWidget(title)
        form = QFormLayout(); form.setHorizontalSpacing(18); form.setVerticalSpacing(10)
        self.name = QLineEdit(seed.name if seed else "Edge Seed")
        self.method = QComboBox(); self.method.addItems(("Size", "Number of divisions")); self.method.setCurrentText(seed.method if seed else "Number of divisions")
        self.size = QDoubleSpinBox(); self.size.setRange(1e-12, 1e30); self.size.setDecimals(9); self.size.setValue(seed.size if seed else 1.0); self.size.setSuffix(f" {unit_system_for(self).symbol('length')}")
        self.divisions = QSpinBox(); self.divisions.setRange(1, 1_000_000); self.divisions.setValue(seed.divisions if seed and seed.divisions else 10)
        self.bias = QComboBox(); self.bias.addItems(("None", "Single", "Double")); self.bias.setCurrentText(seed.bias if seed else "None")
        self.bias_factor = QDoubleSpinBox(); self.bias_factor.setRange(1.0, 1e12); self.bias_factor.setDecimals(6); self.bias_factor.setValue(seed.bias_factor if seed else 1.0)
        form.addRow("Name", self.name); root.addLayout(form)
        root.addWidget(QLabel("Target region"))
        self.target = CompactRegionSelector(project, definition or getattr(seed, "target", RegionDefinition()), options, pick_callback, parent=self)
        root.addWidget(self.target)
        form2 = QFormLayout(); form2.setHorizontalSpacing(18); form2.setVerticalSpacing(10)
        form2.addRow("Method", self.method); form2.addRow("Approximate size", self.size); form2.addRow("Number of divisions", self.divisions); form2.addRow("Distribution", self.bias); form2.addRow("Bias factor", self.bias_factor)
        root.addLayout(form2)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Apply).setObjectName("PrimaryButton")
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(lambda: self.apply_requested.emit(self.values()))
        buttons.rejected.connect(self.close); root.addWidget(buttons)

    def values(self):
        return {
            "name": self.name.text().strip(), "target": self.target.definition(),
            "method": self.method.currentText(), "size": self.size.value(),
            "divisions": self.divisions.value(), "bias": self.bias.currentText(),
            "bias_factor": self.bias_factor.value(),
        }

    def set_selected_definition(self, definition): self.target.set_definition(definition)
    def set_selected_edges(self, definition): self.set_selected_definition(definition)

    def set_divisions(self, value: int):
        self.method.setCurrentText("Number of divisions")
        self.divisions.setValue(max(1, int(value)))
