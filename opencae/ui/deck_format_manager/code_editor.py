"""Provide the monospaced line-numbered editor used for deck templates and previews."""

from __future__ import annotations

from PyQt6.QtCore import QRect, QSize, Qt
from PyQt6.QtGui import QFont, QFontDatabase, QPainter, QPalette
from PyQt6.QtWidgets import QPlainTextEdit, QWidget


class _LineNumberArea(QWidget):
    """Paint line numbers delegated by one ``DeckCodeEditor``."""

    def __init__(self, editor: "DeckCodeEditor"):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        """Reserve exactly the width needed by the editor gutter."""
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event) -> None:
        """Delegate line-number painting to the owning editor."""
        self._editor.paint_line_numbers(event)


class DeckCodeEditor(QPlainTextEdit):
    """Display deck syntax with a fixed-width font and persistent line gutter."""

    def __init__(self, parent=None):
        super().__init__(parent)
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setTabChangesFocus(False)

        self._line_number_area = _LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self._update_line_number_area_width()

    def line_number_area_width(self) -> int:
        """Return gutter width for the current number of document lines."""
        digits = max(2, len(str(max(1, self.blockCount()))))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def paint_line_numbers(self, event) -> None:
        """Paint visible document line numbers into the gutter."""
        painter = QPainter(self._line_number_area)
        painter.fillRect(
            event.rect(),
            self.palette().color(QPalette.ColorRole.AlternateBase),
        )
        painter.setPen(self.palette().color(QPalette.ColorRole.PlaceholderText))

        block = self.firstVisibleBlock()
        number = block.blockNumber()
        top = round(
            self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        )
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.drawText(
                    0,
                    top,
                    self._line_number_area.width() - 6,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(number + 1),
                )
            block = block.next()
            number += 1
            top = bottom
            if block.isValid():
                bottom = top + round(self.blockBoundingRect(block).height())

    def resizeEvent(self, event) -> None:
        """Keep the line-number gutter aligned with the text viewport."""
        super().resizeEvent(event)
        rect = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(
                rect.left(),
                rect.top(),
                self.line_number_area_width(),
                rect.height(),
            )
        )

    def _update_line_number_area_width(self, *_args) -> None:
        """Reserve viewport space whenever the document line count changes."""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy: int) -> None:
        """Scroll or repaint the gutter alongside the text viewport."""
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(
                0,
                rect.y(),
                self._line_number_area.width(),
                rect.height(),
            )
        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width()
