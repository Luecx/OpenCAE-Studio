"""Compact project-switcher affordance embedded in the browser tab."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QToolButton, QWidget


class ButtonProjectSelector(QToolButton):
    def __init__(self, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setText("▾")
        self.setObjectName("ProjectSelectorButton")
        self.setAutoRaise(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(20)
