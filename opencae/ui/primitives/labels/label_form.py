"""Muted label placed above one form control."""

from PyQt6.QtWidgets import QLabel, QWidget


class LabelForm(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(str(text), parent)
        self.setObjectName("PrimaryFieldLabel")
