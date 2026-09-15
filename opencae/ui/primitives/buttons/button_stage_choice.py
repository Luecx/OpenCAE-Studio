"""Exclusive workflow-stage choice used by the main stage bar."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QToolButton, QWidget


class ButtonStageChoice(QToolButton):
    def __init__(self, text: str, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setText(str(text))
        self.setCheckable(True)
        self.setAutoExclusive(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        widths = {
            "BOUNDARY CONDITIONS": 158,
            "CONSTRAINTS": 108,
            "ANALYSIS": 96,
            "STUDIES": 92,
        }
        self.setMinimumWidth(widths.get(str(text), 82))
        self.setFixedHeight(40)
