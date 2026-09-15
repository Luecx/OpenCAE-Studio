"""Destructive dialog/form action button."""

from PyQt6.QtWidgets import QPushButton, QWidget


class ButtonFormDanger(QPushButton):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(str(text), parent)
        self.setObjectName("DangerButton")
