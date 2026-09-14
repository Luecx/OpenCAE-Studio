"""Plain field caption used in the compact Sketcher inspector."""

from PyQt6.QtWidgets import QLabel, QWidget


class LabelSketchField(QLabel):
    """Keep the Sketcher field-caption appearance identical to a native QLabel."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(str(text), parent)
