from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from .solver_row import SolverRow


class SolverSettingsDialog(QDialog):
    def __init__(self, configs, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Solver Settings")
        self.setMinimumWidth(760)
        layout = QVBoxLayout(self)
        label = QLabel("Enable installed solvers and select their executable files.")
        label.setWordWrap(True); layout.addWidget(label)
        self.rows = {name: SolverRow(name, config) for name, config in configs.items()}
        for row in self.rows.values(): layout.addWidget(row)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); layout.addWidget(buttons)

    def values(self):
        return {name: row.values() for name, row in self.rows.items()}
