"""Prominent panel/dialog title label."""

from PyQt6.QtWidgets import QLabel, QWidget


class LabelTitle(QLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(str(text), parent)
        self.setObjectName("PanelTitle")
