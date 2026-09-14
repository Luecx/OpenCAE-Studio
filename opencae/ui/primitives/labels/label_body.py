"""Unstyled semantic body text."""

from PyQt6.QtWidgets import QLabel, QWidget


class LabelBody(QLabel):
    def __init__(self, text: str = "", *, object_name: str = "", parent: QWidget | None = None) -> None:
        super().__init__(str(text), parent)
        if object_name:
            self.setObjectName(object_name)
