"""Compact close-project button used inside the project switcher menu."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QToolButton, QWidget


class ButtonProjectMenuClose(QToolButton):
    def __init__(
        self,
        *,
        tooltip: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setText("−")
        self.setObjectName("ProjectMenuCloseButton")
        self.setAutoRaise(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(26, 26)
        if tooltip:
            self.setToolTip(str(tooltip))
