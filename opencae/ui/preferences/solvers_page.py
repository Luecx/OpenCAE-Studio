from PyQt6.QtWidgets import QVBoxLayout, QWidget

from opencae.ui.dialogs.solver_row import SolverRow


class SolversPage(QWidget):
    def __init__(self, configs, parent=None):
        super().__init__(parent); layout = QVBoxLayout(self)
        self.rows = {name: SolverRow(name, config) for name, config in configs.items()}
        for row in self.rows.values(): layout.addWidget(row)
        layout.addStretch(1)

    def values(self):
        return {name: row.values() for name, row in self.rows.items()}
