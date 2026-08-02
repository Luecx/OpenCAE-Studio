from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem


class JobsPanel(QTableWidget):
    job_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(0, 4, parent)
        self.setHorizontalHeaderLabels(["Job", "Step", "Solver", "Status"])
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionBehavior(self.SelectionBehavior.SelectRows)
        self.cellClicked.connect(self._clicked)

    def refresh(self, project):
        jobs = project.jobs
        self.setRowCount(len(jobs))
        for row, job in enumerate(jobs):
            analysis = project.try_resolve(job.analysis_ref) if job.analysis_ref else None
            values = (job.name, analysis.name if analysis else "All Steps", job.solver, job.status)
            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                cell.setData(Qt.ItemDataRole.UserRole, job.name)
                self.setItem(row, column, cell)

    def _clicked(self, row, _column):
        item = self.item(row, 0)
        if item is not None:
            self.job_requested.emit(str(item.data(Qt.ItemDataRole.UserRole) or item.text()))
