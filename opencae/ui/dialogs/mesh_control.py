from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QVBoxLayout

from opencae.model.selection import RegionDefinition
from opencae.ui.core.widgets import CompactRegionSelector


class MeshControlDialog(QDialog):
    def __init__(self, project, options=(), definition=None, pick_callback=None, control=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mesh Control")
        self.setMinimumWidth(650)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        root = QVBoxLayout(self); root.setContentsMargins(18, 16, 18, 14); root.setSpacing(12)
        title = QLabel("Mesh Control"); title.setObjectName("PanelTitle"); root.addWidget(title)
        form = QFormLayout(); form.setHorizontalSpacing(18); form.setVerticalSpacing(10)
        self.name = QLineEdit(control.name if control else "Mesh Control-1")
        self.scope = QComboBox(); self.scope.addItems(("Edge", "Face", "Cell")); self.scope.setCurrentText(control.scope if control else "Cell")
        self.topology = QComboBox(); self.topology.addItems(("Line", "Triangular", "Quadrilateral", "Tetrahedral", "Pyramidal", "Pentahedral", "Hexahedral")); self.topology.setCurrentText(control.topology if control else "Tetrahedral")
        self.technique = QComboBox(); self.technique.addItems(("Free", "Structured", "Transfinite", "Recombine")); self.technique.setCurrentText(control.technique if control else "Free")
        form.addRow("Name", self.name); form.addRow("Scope", self.scope); root.addLayout(form)
        root.addWidget(QLabel("Target region (empty means all entities of the selected scope)"))
        self._pick_callback = pick_callback
        self.target = CompactRegionSelector(project, definition or getattr(control, "target", RegionDefinition()), options, self._pick, parent=self)
        root.addWidget(self.target)
        form2 = QFormLayout(); form2.addRow("Preferred topology", self.topology); form2.addRow("Technique", self.technique); root.addLayout(form2)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); root.addWidget(buttons)

    def _pick(self, owner, done, finished):
        return self._pick_callback(self.scope.currentText(), owner, done, finished) if self._pick_callback else None

    def values(self):
        return {
            "name": self.name.text().strip(), "scope": self.scope.currentText(),
            "target": self.target.definition(), "topology": self.topology.currentText(),
            "technique": self.technique.currentText(),
        }
