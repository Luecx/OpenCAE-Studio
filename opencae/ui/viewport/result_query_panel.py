"""Provides the compact viewport panel for queried result values and matrices."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QLabel,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from opencae.ui.core.theme import PALETTE
from opencae.ui.templates import FieldStack, SectionHeading

from .result_query_model import QueryResult
from .result_selection_panel import RESULT_INFO_WIDTH


class ResultQueryPanel(QFrame):
    """Show one queried node/element summary plus an optional result matrix."""

    def __init__(self, parent=None):
        """Build the fixed-width result query overlay using canonical field labels."""
        super().__init__(parent)
        self.setObjectName("ResultQueryPanel")
        self.setFixedWidth(RESULT_INFO_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.hide()
        self.setStyleSheet(
            f"QFrame#ResultQueryPanel{{background:{PALETTE['panel']};"
            f"border:1px solid {PALETTE['border_light']};border-radius:7px;}}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)
        self.title = SectionHeading("Result Query")
        layout.addWidget(self.title)

        self.form = FieldStack(spacing=8)
        layout.addWidget(self.form)

        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.hide()
        layout.addWidget(self.table)

    def show_prompt(self, mode):
        """Prompt for the next node or element click using a normal result field."""
        noun = "node" if mode == "node" else "element"
        self.show_result(
            f"Query {noun.title()}",
            QueryResult(summary=[("Selection", f"Click a {noun} in the mesh")]),
        )

    def show_result(self, title, result):
        """Replace the summary/matrix contents with one query result and show the panel."""
        self.title.setText(str(title))
        self._clear()
        rows = result.summary or [("Result", "No values available for this selection")]
        for key, value in rows:
            text = QLabel(str(value))
            text.setObjectName("ResultQueryValue")
            text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            text.setWordWrap(True)
            self.form.addRow(str(key), text)
        if result.matrix:
            self._show_matrix(result.columns, result.matrix)
        self.layout().activate()
        self.adjustSize()
        self.setFixedHeight(self.sizeHint().height())
        self.show()
        self.raise_()

    def _show_matrix(self, columns, values):
        """Render a compact no-scroll matrix beneath the label/value summary."""
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setRowCount(len(values))
        for row, items in enumerate(values):
            for column, value in enumerate(items):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
        self.table.resizeRowsToContents()
        row_height = sum(
            max(24, self.table.rowHeight(row)) for row in range(len(values))
        )
        self.table.setFixedHeight(
            self.table.horizontalHeader().height()
            + row_height
            + 2 * self.table.frameWidth()
            + 2
        )
        self.table.show()

    def clear_query(self):
        """Clear and hide the current query overlay."""
        self._clear()
        self.hide()

    def _clear(self):
        """Reset summary and matrix contents while releasing dynamic field widgets."""
        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        self.form.clear()
        self.table.clearContents()
        self.table.setRowCount(0)
        self.table.hide()
