"""Display persistent Jobs and expose their actions through a row context menu."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QMenu,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from opencae.ui.actions.ids import A


_COLUMN_WEIGHTS = (0.17, 0.23, 0.11, 0.15, 0.34)


class JobsPanel(QWidget):
    """Display project Jobs without duplicating solver output in the main window."""

    def __init__(self, store, jobs, actions, parent=None):
        """Build the synchronized Job table and its context-action surface."""
        super().__init__(parent)
        self.store = store
        self.jobs = jobs
        self.actions = actions
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        self.table = QTableWidget(0, 5)
        self.table.setProperty("flatTable", True)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        self.table.setFrameShape(QFrame.Shape.NoFrame)
        self.table.setMouseTracking(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setHorizontalHeaderLabels(
            ["Job", "Source", "Kind", "Solver", "Status"]
        )
        header = self.table.horizontalHeader()
        header.setProperty("flatTableHeader", True)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setMinimumSectionSize(60)
        header.setMinimumHeight(30)
        header.setStretchLastSection(False)
        header.setHighlightSections(False)
        for column in range(5):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
        self.table.verticalHeader().hide()
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        root.addWidget(self.table, 1)

        store.changed.connect(self.refresh)
        store.runtime_changed.connect(self._runtime_changed)
        jobs.selection_changed.connect(self._manager_selection_changed)
        self.refresh()
        self._resize_columns()

    def resizeEvent(self, event):
        """Keep weighted Job columns proportional to the available dock width."""
        super().resizeEvent(event)
        self._resize_columns()

    def _resize_columns(self):
        """Distribute table width using stable semantic column proportions."""
        available = self.table.viewport().width()
        if available <= 0:
            return
        used = 0
        for column, weight in enumerate(_COLUMN_WEIGHTS[:-1]):
            width = max(60, int(available * weight))
            self.table.setColumnWidth(column, width)
            used += width
        self.table.setColumnWidth(4, max(60, available - used))

    def _runtime_changed(self, entity_id, _fields):
        """Refresh only when the lightweight update belongs to a visible Job."""
        if any(job.id == str(entity_id) for job in self.store.project.jobs):
            self.refresh()

    def refresh(self, *_):
        """Rebuild Job rows while preserving the manager's selected Job."""
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
        self._resize_columns()
        if selected_row >= 0:
            job_id = self._job_id_for_row(selected_row)
            if job_id and job_id != self.jobs.selected_job_id:
                self.jobs.select_job(job_id)

    def _selection_changed(self):
        """Mirror a table selection into JobManager and the project selection."""
        job_id = self._job_id_for_row(self.table.currentRow())
        if job_id:
            self.jobs.select_job(job_id)

    def _manager_selection_changed(self, job_id):
        """Mirror non-table Job selections back into the visible row selection."""
        for row in range(self.table.rowCount()):
            if self._job_id_for_row(row) == str(job_id):
                self.table.blockSignals(True)
                self.table.selectRow(row)
                self.table.blockSignals(False)
                break

    def _show_context_menu(self, pos):
        """Open actions for the Job under the pointer after making it current."""
        item = self.table.itemAt(pos)
        if item is None:
            return
        row = item.row()
        job_id = self._job_id_for_row(row)
        if not job_id:
            return

        # Shared Job actions operate on JobManager's selection, so make the
        # right-clicked row current before evaluating their enabled state.
        self.table.selectRow(row)
        self.jobs.select_job(job_id)

        menu = QMenu(self.table)
        menu.addAction(self.actions.get(A.JOB_MONITOR))
        menu.addAction(self.actions.get(A.JOB_OPEN_RESULTS))
        menu.addSeparator()
        menu.addAction(self.actions.get(A.JOB_STOP))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _job_id_for_row(self, row) -> str:
        """Return the persistent Job id stored on one table row."""
        item = self.table.item(row, 0) if row >= 0 else None
        return (
            str(item.data(Qt.ItemDataRole.UserRole))
            if item is not None
            else ""
        )
