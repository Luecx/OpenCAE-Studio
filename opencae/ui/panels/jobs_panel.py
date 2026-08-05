"""Synchronized job selection, actions and monospace output panel."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from opencae.ui.actions.ids import A
from opencae.ui.core.widgets import MonospaceOutputView


class JobsPanel(QWidget):
    """Display all jobs and exactly the output of the selected job."""

    def __init__(self, store, jobs, actions, parent=None):
        super().__init__(parent)
        self.store = store
        self.jobs = jobs
        self.actions = actions
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        for action_id in (A.JOB_STOP, A.JOB_MONITOR, A.JOB_OPEN_RESULTS):
            button = QToolButton()
            button.setDefaultAction(actions.get(action_id))
            toolbar.addWidget(button)
        toolbar.addStretch(1)
        root.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Job", "Source", "Kind", "Solver", "Status"]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.output = MonospaceOutputView()
        splitter.addWidget(self.table)
        splitter.addWidget(self.output)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        root.addWidget(splitter, 1)

        store.changed.connect(self.refresh)
        jobs.selection_changed.connect(self._manager_selection_changed)
        jobs.output_changed.connect(self._output_changed)
        self.refresh()

    def refresh(self, *_):
        selected = self.jobs.selected_job_id
        values = tuple(self.store.project.jobs)
        self.table.blockSignals(True)
        self.table.setRowCount(len(values))
        selected_row = -1
        for row, job in enumerate(values):
            source = self.store.project.try_resolve(job.source_ref)
            columns = (
                job.name,
                getattr(source, "name", "Unavailable"),
                job.source_kind.title(),
                job.solver,
                job.status,
            )
            for column, value in enumerate(columns):
                cell = QTableWidgetItem(str(value))
                cell.setData(Qt.ItemDataRole.UserRole, job.id)
                self.table.setItem(row, column, cell)
            if job.id == selected:
                selected_row = row
        if selected_row < 0 and values:
            selected_row = len(values) - 1
        if selected_row >= 0:
            self.table.selectRow(selected_row)
        self.table.blockSignals(False)
        if selected_row >= 0:
            job_id = str(
                self.table.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)
            )
            if job_id != self.jobs.selected_job_id:
                self.jobs.select_job(job_id)
            else:
                self.output.set_output(self.jobs.output_for(job_id))
        else:
            self.output.clear()

    def _selection_changed(self):
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        if item is not None:
            self.jobs.select_job(str(item.data(Qt.ItemDataRole.UserRole)))

    def _manager_selection_changed(self, job_id):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None and str(item.data(Qt.ItemDataRole.UserRole)) == str(job_id):
                self.table.blockSignals(True)
                self.table.selectRow(row)
                self.table.blockSignals(False)
                break
        self.output.set_output(self.jobs.output_for(job_id))

    def _output_changed(self, job_id, text):
        if str(job_id) == self.jobs.selected_job_id:
            self.output.set_output(text)
