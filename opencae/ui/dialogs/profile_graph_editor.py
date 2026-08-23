"""Provides the editable node and segment tables for graph profiles."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from opencae.ui.templates import FieldLabel, apply_inline_action_size


class GraphProfileEditor(QWidget):
    """Edit graph nodes and thickness-bearing segments as compact tables."""

    def __init__(self, nodes="", segments="", parent=None):
        """Build and populate the node and segment table panes."""
        super().__init__(parent)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        self.nodes = self._table(("ID", "y", "z"))
        self.segments = self._table(("Node 1", "Node 2", "Thickness"))
        root.addWidget(self._pane("Local nodes", self.nodes, self._add_node))
        root.addWidget(self._pane("Segments", self.segments, self._add_segment))
        self._load(self.nodes, nodes, 3)
        self._load(self.segments, segments, 3)

    @staticmethod
    def _table(headers: Iterable[str]) -> QTableWidget:
        """Create one stretch-column table for a graph data kind."""
        headers = tuple(headers)
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setMinimumHeight(220)
        return table

    def _pane(
        self,
        title: str,
        table: QTableWidget,
        add: Callable[[], None],
    ) -> QWidget:
        """Build a titled table pane with shared-size add and remove actions."""
        pane = QWidget()
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(FieldLabel(title))
        layout.addWidget(table)

        row = QHBoxLayout()
        row.setSpacing(6)
        plus = QToolButton()
        plus.setText("+")
        plus.setObjectName("InlineAddButton")
        apply_inline_action_size(plus)
        minus = QToolButton()
        minus.setText("−")
        minus.setObjectName("InlineRemoveButton")
        apply_inline_action_size(minus)
        plus.clicked.connect(add)
        minus.clicked.connect(lambda: self._remove(table))
        row.addWidget(plus)
        row.addWidget(minus)
        row.addStretch(1)
        layout.addLayout(row)
        return pane

    def _add_node(self) -> None:
        """Append a node row with a new suggested integer identifier."""
        self._append(self.nodes, (self.nodes.rowCount() + 1, 0.0, 0.0))

    def _add_segment(self) -> None:
        """Append a segment row with neutral default references and thickness."""
        self._append(self.segments, (1, 2, 1.0))

    @staticmethod
    def _append(table: QTableWidget, values: Iterable) -> None:
        """Append one complete row to a graph table."""
        row = table.rowCount()
        table.insertRow(row)
        for column, value in enumerate(values):
            table.setItem(row, column, QTableWidgetItem(str(value)))

    @staticmethod
    def _remove(table: QTableWidget) -> None:
        """Remove selected rows or the final row when nothing is selected."""
        rows = sorted(
            {index.row() for index in table.selectedIndexes()},
            reverse=True,
        )
        if not rows and table.rowCount():
            rows = [table.rowCount() - 1]
        for row in rows:
            table.removeRow(row)

    def _load(self, table: QTableWidget, text, width: int) -> None:
        """Load complete comma-separated rows and ensure one editable row."""
        for line in str(text).replace(";", "\n").splitlines():
            values = [item.strip() for item in line.split(",")]
            if len(values) == width:
                self._append(table, values)
        if not table.rowCount():
            defaults = (1, 0, 0) if table is self.nodes else (1, 2, 1.0)
            self._append(table, defaults)

    @staticmethod
    def _text(table: QTableWidget) -> str:
        """Serialize current rows into the model's comma-separated format."""
        return "\n".join(
            ",".join(
                table.item(row, column).text().strip()
                if table.item(row, column)
                else ""
                for column in range(table.columnCount())
            )
            for row in range(table.rowCount())
        )

    def values(self) -> dict[str, str]:
        """Return the current nodes and segments persistence payload."""
        return {
            "nodes": self._text(self.nodes),
            "segments": self._text(self.segments),
        }

    def connect_changed(self, callback: Callable) -> None:
        """Notify one refresh callback for cell edits and structural row changes."""
        for table in (self.nodes, self.segments):
            table.itemChanged.connect(callback)
            table.model().rowsInserted.connect(callback)
            table.model().rowsRemoved.connect(callback)
