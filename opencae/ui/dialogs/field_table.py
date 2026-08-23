"""Provides the editable tabular data grid used by FieldDefinitionDialog."""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from opencae.ui.templates import button


class FieldTable(QWidget):
    """Edit field rows whose first column is an entity ID and remaining columns are values."""

    def __init__(self, components=1, rows=None, parent=None):
        """Build the table and seed it from persisted rows or a small empty working set."""
        super().__init__(parent)
        self.components = components
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.table = QTableWidget()
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(8)
        add = button("Add row")
        remove = button("Remove row")
        add.clicked.connect(self.add_row)
        remove.clicked.connect(self.remove_row)
        actions.addWidget(add)
        actions.addWidget(remove)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.set_components(components)
        for values in rows or ():
            self.add_row(values)
        if not rows:
            for _ in range(6):
                self.add_row()

    def set_components(self, count) -> None:
        """Resize component columns while retaining existing cell text where possible."""
        self.components = max(1, int(count))
        old = self.values() if self.table.columnCount() else []
        self.table.setColumnCount(self.components + 1)
        self.table.setHorizontalHeaderLabels(
            ["ID", *[f"C{i + 1}" for i in range(self.components)]]
        )
        if old:
            self.table.setRowCount(0)
            for values in old:
                self.add_row(values)

    def add_row(self, values=None) -> None:
        """Append one editable row, optionally initialized from persisted cell values."""
        row = self.table.rowCount()
        self.table.insertRow(row)
        values = values if isinstance(values, (list, tuple)) else ()
        for column in range(self.table.columnCount()):
            text = str(values[column]) if column < len(values) else ""
            self.table.setItem(row, column, QTableWidgetItem(text))

    def remove_row(self) -> None:
        """Remove every table row touched by the current selection."""
        rows = sorted(
            {index.row() for index in self.table.selectedIndexes()},
            reverse=True,
        )
        for row in rows:
            self.table.removeRow(row)

    def values(self) -> list[list[str]]:
        """Return non-empty rows as normalized strings in visible column order."""
        result = []
        for row in range(self.table.rowCount()):
            values = [
                self.table.item(row, column).text().strip()
                if self.table.item(row, column)
                else ""
                for column in range(self.table.columnCount())
            ]
            if any(values):
                result.append(values)
        return result
