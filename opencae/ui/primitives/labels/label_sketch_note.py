"""Word-wrapped explanatory note used in the Sketcher inspector."""

from PyQt6.QtWidgets import QLabel, QWidget


class LabelSketchNote(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(str(text), parent)
        self.setObjectName("SketchAxisNote")
        self.setWordWrap(True)
