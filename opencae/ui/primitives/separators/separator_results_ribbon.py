"""Vertical divider preserving the compact Results-ribbon spacing."""

from PyQt6.QtWidgets import QFrame, QWidget


class SeparatorResultsRibbon(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ResultsRibbonSeparator")
        self.setFrameShape(QFrame.Shape.VLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        self.setFixedWidth(10)
        self.setContentsMargins(4, 8, 4, 8)
