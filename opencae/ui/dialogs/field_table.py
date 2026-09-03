"""Provides the editable tabular data grid used by FieldDefinitionDialog."""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from opencae.ui.templates import button


_ADDRESS_COLUMNS = {
    "Nodal": ("Node",),
    "Element": ("Element",),
    "Element-Nodal": ("Element", "Local node"),
    "Integration Point": ("Element", "Local IP"),
    "Material Point": ("Element", "Local IP", "Local MP"),
    "Shell Normal": ("Element", "Local node"),
}


class FieldTable(QWidget):
    """Edit field rows with domain-specific address columns plus component values."""

    def __init__(self, components=1, rows=None, parent=None, location="Nodal"):
        """Build the table and seed it from persisted rows or a small empty working set."""
        super().__init__(parent)
        self.components = max(1, int(components))
        self.location = str(location or "Nodal")
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

        self._configure_columns()
        for values in rows or ():
            self.add_row(values)
        if not rows:
            for _ in range(6):
                self.add_row()

    def set_components(self, count) -> None:
        """Resize component columns while retaining existing cell text where possible."""
        self.set_domain(self.location, count)

    def set_domain(self, location, components=None) -> None:
        """Switch address topology and component count while retaining entered rows."""
        old = self.values() if self.table.columnCount() else []
        self.location = str(location or "Nodal")
        if components is not None:
            self.components = max(1, int(components))
        self._configure_columns()
        if old:
            self.table.setRowCount(0)
            for values in old:
                self.add_row(values)

    def _configure_columns(self) -> None:
        address = _ADDRESS_COLUMNS.get(self.location, ("ID",))
        self.table.setColumnCount(len(address) + self.components)
        self.table.setHorizontalHeaderLabels(
            [*address, *[f"C{i + 1}" for i in range(self.components)]]
        )

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
