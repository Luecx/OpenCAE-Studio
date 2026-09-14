"""Section heading used to divide editor forms."""

from PyQt6.QtWidgets import QLabel, QWidget


class LabelSection(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(str(text), parent)
        self.setObjectName("EditorSectionHeading")
