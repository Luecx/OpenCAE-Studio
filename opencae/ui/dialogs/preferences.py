from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QMessageBox, QStackedWidget, QVBoxLayout

from opencae.ui.preferences import GeneralPage, PreferencesNavigation, SolversPage, UnitSystemsPage


class PreferencesDialog(QDialog):
    def __init__(self, settings, parent=None, initial_page="General"):
        super().__init__(parent); self.settings = settings; self.setWindowTitle("Preferences"); self.resize(1040, 700)
        root = QVBoxLayout(self); body = QHBoxLayout(); self.navigation = PreferencesNavigation(); self.stack = QStackedWidget()
        body.addWidget(self.navigation); body.addWidget(self.stack, 1); root.addLayout(body, 1)
        self.general = GeneralPage(settings); self.solvers = SolversPage(settings.solver_configs)
        self.units = UnitSystemsPage(settings.unit_systems, settings.selected_unit_system)
        for title, page in (("General", self.general), ("Solvers", self.solvers), ("Unit Systems", self.units)):
            self.navigation.add_page(title); self.stack.addWidget(page)
        self.navigation.currentRowChanged.connect(self.stack.setCurrentIndex); self.navigation.setCurrentRow({"General": 0, "Solvers": 1, "Unit Systems": 2}.get(initial_page, 0))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept); buttons.rejected.connect(self.reject); root.addWidget(buttons)

    def _accept(self):
        error = self.units.validate()
        if error: QMessageBox.warning(self, "Invalid unit systems", error); return
        self.accept()

    def values(self):
        systems, selected = self.units.values(); values = self.general.values()
        values.update({"solver_configs": self.solvers.values(), "unit_systems": systems, "selected_unit_system": selected})
        return values
