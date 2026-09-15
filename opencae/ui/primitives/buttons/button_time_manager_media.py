"""Compact media-control button used by the result Time Manager."""

from PyQt6.QtCore import QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QToolButton, QWidget


class ButtonTimeManagerMedia(QToolButton):
    def __init__(
        self,
        *,
        icon: QIcon,
        tooltip: str = "",
        checkable: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("TimeManagerControl")
        self.setIcon(icon)
        self.setIconSize(QSize(18, 18))
        self.setCheckable(bool(checkable))
        if tooltip:
            self.setToolTip(str(tooltip))
        self.setFixedSize(28, 28)
