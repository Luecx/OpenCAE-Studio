"""Inspector heading used by the Sketcher side panel."""

from PyQt6.QtWidgets import QLabel, QWidget


class LabelSketchHeading(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(str(text), parent)
        self.setObjectName("SketchInspectorHeading")
