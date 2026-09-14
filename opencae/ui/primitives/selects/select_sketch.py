"""Native QComboBox surface used in the compact Sketcher inspector."""

from PyQt6.QtWidgets import QComboBox, QWidget


class SelectSketch(QComboBox):
    """Preserve the Sketcher inspector's pre-refactor native dropdown chrome."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
