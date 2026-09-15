"""Unstyled semantic body text."""

from PyQt6.QtWidgets import QLabel, QWidget


class LabelBody(QLabel):
    def __init__(
        self,
        text: str = "",
        parent: QWidget | None = None,
        *,
        object_name: str = "",
    ) -> None:
        super().__init__(str(text), parent)
        if object_name:
            self.setObjectName(object_name)
