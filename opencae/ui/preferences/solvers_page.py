"""Provides the solver backend page inside application Preferences."""

from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from opencae.ui.dialogs.solver_row import SolverRow
from opencae.ui.templates import FieldLabel, SectionHeading


class SolversPage(QWidget):
    """Edit all persisted solver executable configurations."""

    def __init__(self, configs, parent=None):
        """Build one semantic configuration section for each solver backend."""
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        layout.addWidget(SectionHeading("Solver Backends"))
        hint = FieldLabel("Enable installed solvers and select their executable files.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.rows = {name: SolverRow(name, config) for name, config in configs.items()}
        for name, row in self.rows.items():
            layout.addWidget(SectionHeading(str(name)))
            layout.addWidget(row)
        layout.addStretch(1)

    def values(self):
        """Return persisted configuration values keyed by solver name."""
        return {name: row.values() for name, row in self.rows.items()}
