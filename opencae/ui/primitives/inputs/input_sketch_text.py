"""Native-height text input used in the compact Sketcher inspector."""

from PyQt6.QtWidgets import QLineEdit, QWidget


class InputSketchText(QLineEdit):
    """Keep the Sketcher inspector's pre-refactor native QLineEdit geometry."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(str(text), parent)
