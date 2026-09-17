"""Compact muted section heading used by the result Time Manager sidebar."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QWidget

from opencae.ui.foundation.theme import PALETTE


class LabelTimeManagerHeading(QLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(str(text), parent)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.setStyleSheet(
            f"color:{PALETTE['muted']};font-weight:600;font-size:9pt;"
        )
