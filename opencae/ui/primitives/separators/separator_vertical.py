"""Canonical vertical divider between editor surfaces."""

from PyQt6.QtWidgets import QFrame, QWidget


class SeparatorVertical(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("EditorVerticalSeparator")
        self.setFrameShape(QFrame.Shape.VLine)
        self.setFrameShadow(QFrame.Shadow.Plain)
