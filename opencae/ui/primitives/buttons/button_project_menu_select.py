"""Text-only project selection row button used inside the project switcher menu."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QSizePolicy, QToolButton, QWidget


class ButtonProjectMenuSelect(QToolButton):
    def __init__(
        self,
        text: str,
        *,
        tooltip: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setText(str(text))
        self.setObjectName("ProjectMenuSelectButton")
        self.setAutoRaise(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(180)
        if tooltip:
            self.setToolTip(str(tooltip))
