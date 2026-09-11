"""Solver backend configuration inside the unified application Settings dialog."""

from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from opencae.ui.core.widgets import ChevronComboBox
from opencae.ui.dialogs.solver_row import SolverRow
from opencae.ui.templates import FieldLabel, SectionHeading, apply_primary_control_height, field_block


class SolversPage(QWidget):
    """Edit the default solver plus executable configuration for every backend."""

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        title = FieldLabel("Solvers")
        title.setObjectName("PreferencesPageTitle")
        layout.addWidget(title)
        description = FieldLabel(
            "Configure solver executables once for the whole application. Analyses still store the solver they were created with."
        )
        description.setObjectName("PreferencesPageDescription")
        description.setWordWrap(True)
        layout.addWidget(description)
        layout.addSpacing(6)

        layout.addWidget(SectionHeading("Default backend"))
        self.default_solver = ChevronComboBox()
        self.default_solver.addItems(tuple(settings.solver_configs))
        self.default_solver.setCurrentText(
            settings.selected_solver or next(iter(settings.solver_configs), "")
        )
        apply_primary_control_height(self.default_solver)
        layout.addWidget(field_block("Default solver for new analyses", self.default_solver))

        layout.addWidget(SectionHeading("Solver backends"))
        hint = FieldLabel(
            "Enable installed solvers, choose their executable and define optional command-line arguments."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.rows = {
            name: SolverRow(name, config)
            for name, config in settings.solver_configs.items()
        }
        for name, row in self.rows.items():
            layout.addWidget(SectionHeading(str(name)))
            layout.addWidget(row)
        layout.addStretch(1)

    def values(self) -> dict[str, object]:
        """Return the selected default plus persisted backend configurations."""
        return {
            "selected_solver": self.default_solver.currentText(),
            "solver_configs": {
                name: row.values()
                for name, row in self.rows.items()
            },
        }
