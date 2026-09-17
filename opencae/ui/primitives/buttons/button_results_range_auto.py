"""Compact one-shot auto-range icon used inside the Results contour flyout."""

from PyQt6.QtCore import QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QToolButton, QWidget

from opencae.ui.foundation.metrics import PRIMARY_CONTROL_HEIGHT


class ButtonResultsRangeAuto(QToolButton):
    def __init__(
        self,
        icon: QIcon,
        *,
        tooltip: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ResultRangeAutoIcon")
        self.setCheckable(False)
        self.setIcon(icon)
        self.setIconSize(QSize(16, 16))
        self.setFixedSize(30, PRIMARY_CONTROL_HEIGHT)
        if tooltip:
            self.setToolTip(tooltip)
