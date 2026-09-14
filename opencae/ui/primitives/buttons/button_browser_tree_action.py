"""Compact expand/collapse button used by tree browser toolbars."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QToolButton, QWidget


class ButtonBrowserTreeAction(QToolButton):
    def __init__(self, text: str, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setText(str(text))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(28, 28)
