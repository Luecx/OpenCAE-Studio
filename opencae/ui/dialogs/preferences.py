"""Provides the multi-page application Preferences dialog."""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QHBoxLayout, QMessageBox, QStackedWidget, QWidget

from opencae.ui.preferences import GeneralPage, PreferencesNavigation, SolversPage, UnitSystemsPage
from opencae.ui.templates import VerticalSeparator, dialog_buttons, dialog_layout


class PreferencesDialog(QDialog):
    """Edit general, solver and unit-system settings in one persistent page shell."""

    def __init__(self, settings, parent=None, initial_page="General"):
        """Build left navigation and right preference pages with canonical dialog spacing."""
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Preferences")
        self.resize(1080, 720)

        root = dialog_layout(self)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(20)

        self.navigation = PreferencesNavigation()
        body.addWidget(self.navigation)
        body.addWidget(VerticalSeparator())

        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)
        root.addLayout(body, 1)

        self.general = GeneralPage(settings)
        self.solvers = SolversPage(settings.solver_configs)
        self.units = UnitSystemsPage(settings.unit_systems, settings.selected_unit_system)
        for title, page in (
            ("General", self.general),
            ("Solvers", self.solvers),
            ("Unit Systems", self.units),
        ):
            self.navigation.add_page(title)
            self.stack.addWidget(page)

        self.navigation.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.navigation.setCurrentRow(
            {"General": 0, "Solvers": 1, "Unit Systems": 2}.get(initial_page, 0)
        )

        buttons = dialog_buttons()
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _accept(self):
        """Validate editable unit systems before closing Preferences successfully."""
        error = self.units.validate()
        if error:
            QMessageBox.warning(self, "Invalid unit systems", error)
            return
        self.accept()

    def values(self):
        """Return all edited application settings in the controller's expected shape."""
        systems, selected = self.units.values()
        values = self.general.values()
        values.update(
            {
                "solver_configs": self.solvers.values(),
                "unit_systems": systems,
                "selected_unit_system": selected,
            }
        )
        return values
