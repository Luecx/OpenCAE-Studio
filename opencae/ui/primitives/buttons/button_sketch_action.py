"""Native QPushButton action used in the compact Sketcher inspector."""

from PyQt6.QtWidgets import QPushButton, QWidget


class ButtonSketchAction(QPushButton):
    """Preserve the Sketcher inspector's pre-refactor QPushButton surface."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(str(text), parent)
