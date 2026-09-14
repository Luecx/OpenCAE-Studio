"""Provides the editable node and segment tables for graph profiles."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from opencae.ui.primitives.buttons import ButtonInlineAction
from opencae.ui.templates import FieldLabel


class GraphProfileEditor(QWidget):
    """Edit graph nodes and thickness-bearing segments as compact tables."""

    def __init__(self, nodes="", segments="", parent=None):
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
        pane = QWidget()
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(FieldLabel(title))
        layout.addWidget(table)

        row = QHBoxLayout()
        row.setSpacing(6)
        plus = ButtonInlineAction("+", object_name="InlineAddButton", parent=pane)
        minus = ButtonInlineAction("−", object_name="InlineRemoveButton", parent=pane)
        plus.clicked.connect(add)
        minus.clicked.connect(lambda: self._remove(table))
        row.addWidget(plus)
        row.addWidget(minus)
        row.addStretch(1)
        layout.addLayout(row)
        return pane

    def _add_node(self) -> None:
        self._append(self.nodes, (self.nodes.rowCount() + 1, 0.0, 0.0))

    def _add_segment(self) -> None:
        self._append(self.segments, (1, 2, 1.0))

    @staticmethod
    def _append(table: QTableWidget, values: Iterable) -> None:
        row = table.rowCount()
        table.insertRow(row)
        for column, value in enumerate(values):
            table.setItem(row, column, QTableWidgetItem(str(value)))

    @staticmethod
    def _remove(table: QTableWidget) -> None:
        rows = sorted({index.row() for index in table.selectedIndexes()}, reverse=True)
        if not rows and table.rowCount():
            rows = [table.rowCount() - 1]
        for row in rows:
            table.removeRow(row)

    def _load(self, table: QTableWidget, text, width: int) -> None:
        for line in str(text).replace(";", "\n").splitlines():
            values = [item.strip() for item in line.split(",")]
            if len(values) == width:
                self._append(table, values)
        if not table.rowCount():
            defaults = (1, 0, 0) if table is self.nodes else (1, 2, 1.0)
            self._append(table, defaults)

    @staticmethod
    def _text(table: QTableWidget) -> str:
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
        return {"nodes": self._text(self.nodes), "segments": self._text(self.segments)}

    def connect_changed(self, callback: Callable) -> None:
        for table in (self.nodes, self.segments):
            table.itemChanged.connect(callback)
            table.model().rowsInserted.connect(callback)
            table.model().rowsRemoved.connect(callback)
