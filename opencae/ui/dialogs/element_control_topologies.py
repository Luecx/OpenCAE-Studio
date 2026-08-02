from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem


class ElementTopologyTable(QTableWidget):
    topology_changed = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(0, 4, parent); self.setHorizontalHeaderLabels(("Topology", "Elements", "First", "Second"))
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.verticalHeader().hide(); self.setMinimumHeight(155)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, 4): self.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.itemSelectionChanged.connect(self._emit)

    def set_summaries(self, summaries, preferred=None):
        self.setRowCount(0)
        for summary in summaries:
            row = self.rowCount(); self.insertRow(row)
            values = (summary.label, f"{summary.count:,}", f"{summary.first:,}", f"{summary.second:,}")
            for column, value in enumerate(values):
                item = QTableWidgetItem(value); item.setData(Qt.ItemDataRole.UserRole, summary); self.setItem(row, column, item)
            if summary.key == preferred: self.selectRow(row)
        if self.rowCount() and not self.selectedItems(): self.selectRow(0)

    def select_key(self, key):
        for row in range(self.rowCount()):
            summary = self.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if summary.key == key: self.selectRow(row); return

    def summary(self):
        rows = self.selectionModel().selectedRows()
        return self.item(rows[0].row(), 0).data(Qt.ItemDataRole.UserRole) if rows else None

    def _emit(self): self.topology_changed.emit(self.summary())
