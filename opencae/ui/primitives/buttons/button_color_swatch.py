"""Small expanding color swatch used by color-selection controls."""

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QSizePolicy, QToolButton, QWidget


class ButtonColorSwatch(QToolButton):
    def __init__(
        self,
        value: str,
        *,
        tooltip: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ResultContourColorButton")
        self.setMinimumWidth(72)
        self.setFixedHeight(22)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        if tooltip:
            self.setToolTip(tooltip)
        self.set_color(value)

    def set_color(self, value: str) -> None:
        color = QColor(value)
        self.setText("")
        self.setStyleSheet(
            "QToolButton {"
            f"background-color: {color.name()};"
            "border: 1px solid rgba(255,255,255,0.28);"
            "border-radius: 3px; padding: 0;"
            "}"
            "QToolButton:hover { border: 1px solid rgba(255,255,255,0.72); }"
        )
