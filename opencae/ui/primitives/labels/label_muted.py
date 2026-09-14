"""Secondary muted text label."""

from PyQt6.QtWidgets import QLabel, QWidget


class LabelMuted(QLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(str(text), parent)
        self.setObjectName("MutedLabel")
