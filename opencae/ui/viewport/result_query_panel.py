"""Provides the compact viewport panel for queried result values and matrices."""

from __future__ import annotations

from PyQt6.QtCore import QTimer, Qt
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
from .viewport_overlay_metrics import VIEWPORT_OVERLAY_MARGIN


class ResultQueryPanel(QFrame):
    """Show one queried node/element summary plus an optional result matrix."""

    def __init__(self, parent=None):
        """Build the fixed-width result query overlay using canonical field labels."""
        super().__init__(parent)
        self.setObjectName("ResultQueryPanel")
        self.setFixedWidth(RESULT_INFO_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        self.hide()
        self.refresh_theme()

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
        self.table.setWordWrap(True)
        self.table.hide()
        layout.addWidget(self.table)

    def refresh_theme(self):
        self.setStyleSheet(
            f"QFrame#ResultQueryPanel{{background:{PALETTE['panel']};"
            f"border:1px solid {PALETTE['border_light']};border-radius:7px;}}"
        )

    def show_prompt(self, mode):
        """Prompt for the next node or element click using a normal result field."""
        noun = "node" if mode == "node" else "element"
        self.show_result(
            f"Query {noun.title()}",
            QueryResult(summary=[("Selection", f"Click a {noun} in the mesh")]),
        )

    def show_result(self, title, result):
        """Replace contents and size the overlay after Qt resolves wrapped text."""
        self.title.setText(str(title))
        self._clear()
        rows = result.summary or [("Result", "No values available for this selection")]
        for key, value in rows:
            text = QLabel(str(value))
            text.setObjectName("ResultQueryValue")
            text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            text.setWordWrap(True)
            text.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Minimum,
            )
            self.form.addRow(str(key), text)
        if result.matrix:
            self._show_matrix(result.columns, result.matrix)

        self.show()
        self._fit_to_contents()
        # Wrapped labels and stretched table columns receive their final widths
        # only after one event turn. Refit once more to avoid stale height hints.
        QTimer.singleShot(0, self._fit_to_contents)
        self.raise_()

    def _show_matrix(self, columns, values):
        """Populate the query matrix; final row heights are resolved after show."""
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setRowCount(len(values))
        for row, items in enumerate(values):
            for column, value in enumerate(items):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
        self.table.show()

    def _fit_to_contents(self):
        """Resize the panel to natural content without extending below the viewport."""
        if not self.isVisible():
            return

        layout = self.layout()
        margins = layout.contentsMargins()
        content_width = max(
            1,
            self.width() - margins.left() - margins.right(),
        )
        self.form.setFixedWidth(content_width)
        self.form.updateGeometry()
        if self.form.layout() is not None:
            self.form.layout().invalidate()
            self.form.layout().activate()

        table_height = 0
        if self.table.isVisible():
            self.table.setFixedWidth(content_width)
            self.table.horizontalHeader().resizeSections(QHeaderView.ResizeMode.Stretch)
            self.table.resizeRowsToContents()
            table_height = (
                self.table.horizontalHeader().height()
                + sum(
                    max(24, self.table.rowHeight(row))
                    for row in range(self.table.rowCount())
                )
                + 2 * self.table.frameWidth()
                + 2
            )

        layout.invalidate()
        layout.activate()
        chrome_height = (
            margins.top()
            + margins.bottom()
            + self.title.sizeHint().height()
            + self.form.sizeHint().height()
            + layout.spacing()
        )
        if self.table.isVisible():
            chrome_height += layout.spacing()

        desired_height = chrome_height + table_height
        parent = self.parentWidget()
        available_height = (
            max(
                120,
                parent.height() - self.y() - VIEWPORT_OVERLAY_MARGIN,
            )
            if parent is not None
            else desired_height
        )

        if self.table.isVisible():
            available_table = max(84, available_height - chrome_height)
            visible_table_height = min(table_height, available_table)
            self.table.setFixedHeight(visible_table_height)
            self.table.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
                if visible_table_height < table_height
                else Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            desired_height = chrome_height + visible_table_height

        self.resize(self.width(), min(desired_height, available_height))
        self.updateGeometry()

    def clear_query(self):
        """Clear and hide the current query overlay."""
        self._clear()
        self.hide()

    def _clear(self):
        """Reset summary and matrix contents while releasing dynamic field widgets."""
        self.form.clear()
        self.table.clearContents()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.hide()
