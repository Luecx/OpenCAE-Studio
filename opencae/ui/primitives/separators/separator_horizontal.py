"""Canonical horizontal divider inside forms and option panels."""

from PyQt6.QtWidgets import QFrame, QWidget


class SeparatorHorizontal(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Plain)
