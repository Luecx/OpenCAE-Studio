"""Provides the application solver configuration dialog."""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog

from opencae.ui.templates import FieldLabel, SectionHeading, dialog_buttons, dialog_layout

from .solver_row import SolverRow


class SolverSettingsDialog(QDialog):
    """Configure enabled solver backends and their executable paths."""

    def __init__(self, configs, parent=None):
        """Build one canonical configuration section per registered solver."""
        super().__init__(parent)
        self.setWindowTitle("Solver Settings")
        self.setMinimumSize(760, 420)

        layout = dialog_layout(self)
        layout.addWidget(SectionHeading("Installed Solvers"))
        hint = FieldLabel("Enable available solvers and select their executable files.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.rows = {name: SolverRow(name, config) for name, config in configs.items()}
        for name, row in self.rows.items():
            layout.addWidget(SectionHeading(str(name)))
            layout.addWidget(row)
        layout.addStretch(1)

        buttons = dialog_buttons()
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        """Return normalized solver configuration values by solver name."""
        return {name: row.values() for name, row in self.rows.items()}
