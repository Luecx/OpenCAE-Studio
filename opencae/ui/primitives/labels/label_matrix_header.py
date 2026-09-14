"""Compact centered label used for matrix row and column headers."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QWidget


class LabelMatrixHeader(QLabel):
    def __init__(self, text: str = "", *, parent: QWidget | None = None) -> None:
        super().__init__(str(text), parent)
        self.setObjectName("MatrixHeader")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
