"""Compact persistent link-toggle used by the Results contour range editor."""

from PyQt6.QtCore import QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QToolButton, QWidget


class ButtonResultsRangeSymmetry(QToolButton):
    def __init__(self, icon: QIcon, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ResultRangeSymmetryButton")
        self.setCheckable(True)
        self.setAutoRaise(False)
        self.setIcon(icon)
        self.setIconSize(QSize(18, 18))
        self.setFixedSize(30, 26)
        self.setToolTip("Couple minimum and maximum symmetrically around zero")
