"""Menu button primitive for compact status-bar selectors."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QToolButton, QWidget


class ButtonStatusMenu(QToolButton):
    """Open a whole-target status menu while preserving status-bar geometry."""

    def __init__(
        self,
        text: str = "",
        *,
        object_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setText(str(text))
        if object_name:
            self.setObjectName(str(object_name))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
