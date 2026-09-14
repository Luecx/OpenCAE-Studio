"""Status label used in the Sketcher footer."""

from PyQt6.QtWidgets import QLabel, QWidget


class LabelSketchStatus(QLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(str(text), parent)
        self.setObjectName("SketchStatus")
