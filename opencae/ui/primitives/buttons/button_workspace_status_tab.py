"""Checkable status-bar tab used to expose the lower workspace."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QToolButton, QWidget


class ButtonWorkspaceStatusTab(QToolButton):
    """Preserve the compact Jobs/Log/Time Manager status-tab surface."""

    def __init__(self, text: str, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setText(str(text))
        self.setCheckable(True)
        self.setAutoRaise(False)
        self.setProperty("workspaceStatusTab", True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
