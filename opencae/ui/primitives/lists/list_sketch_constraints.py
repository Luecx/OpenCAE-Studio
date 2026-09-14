"""Constraint list surface used in the Sketcher inspector."""

from PyQt6.QtWidgets import QListWidget, QWidget


class ListSketchConstraints(QListWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SketchConstraintList")
