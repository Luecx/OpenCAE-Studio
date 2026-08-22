"""Synchronized job selection and full-width solver output panel."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHeaderView,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from opencae.ui.core.widgets import MonospaceOutputView


_COLUMN_WEIGHTS = (0.17, 0.23, 0.11, 0.15, 0.34)


class JobsPanel(QWidget):
    """Display all jobs above exactly the output of the selected job."""

    def __init__(self, store, jobs, actions, parent=None):
        super().__init__(parent)
        self.store = store
        self.jobs = jobs
        self.actions = actions
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Job", "Source", "Kind", "Solver", "Status"]
        )
        header = self.table.horizontalHeader()
        header.setMinimumSectionSize(60)
        header.setStretchLastSection(False)
        for column in range(5):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self._selection_changed)

        minimum_table_height = (
            header.sizeHint().height()
            + self.table.verticalHeader().defaultSectionSize()
            + 8
        )
        self.table.setMinimumHeight(minimum_table_height)

        self.output = MonospaceOutputView()
        splitter.addWidget(self.table)
        splitter.addWidget(self.output)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setCollapsible(0, False)
        splitter.setSizes([95, 140])
        root.addWidget(splitter, 1)

        store.changed.connect(self.refresh)
        jobs.selection_changed.connect(self._manager_selection_changed)
        jobs.output_changed.connect(self._output_changed)
        self.refresh()
        self._resize_columns()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_columns()

    def _resize_columns(self):
        available = self.table.viewport().width()
        if available <= 0:
            return
        used = 0
        for column, weight in enumerate(_COLUMN_WEIGHTS[:-1]):
            width = max(60, int(available * weight))
            self.table.setColumnWidth(column, width)
            used += width
        self.table.setColumnWidth(4, max(60, available - used))

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
