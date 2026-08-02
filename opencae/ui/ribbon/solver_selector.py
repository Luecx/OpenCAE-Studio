from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout

from opencae.ui.core.widgets import ChevronComboBox


class SolverSelector(QFrame):
    def __init__(self, settings, changed, parent=None):
        super().__init__(parent)
        self.settings = settings; self.changed = changed
        layout = QVBoxLayout(self); layout.setContentsMargins(9, 8, 9, 4); layout.setSpacing(5)
        self.combo = ChevronComboBox(); self.combo.setMinimumWidth(190)
        self.combo.currentTextChanged.connect(self._selected)
        title = QLabel("ACTIVE SOLVER"); title.setAlignment(Qt.AlignmentFlag.AlignCenter); title.setObjectName("RibbonGroupTitle")
        layout.addWidget(self.combo); layout.addWidget(title)
        self.refresh()

    def refresh(self):
        enabled = self.settings.enabled_solvers()
        current = self.settings.selected_solver if self.settings.selected_solver in enabled else ""
        self.combo.blockSignals(True); self.combo.clear(); self.combo.addItem("No solver")
        self.combo.addItems(enabled); self.combo.setCurrentText(current or "No solver"); self.combo.blockSignals(False)
        self.settings.selected_solver = current

    def _selected(self, text):
        self.settings.selected_solver = "" if text == "No solver" else text
        self.changed()
