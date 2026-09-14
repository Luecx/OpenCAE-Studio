"""Accent group title shown below expanded ribbon actions."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QWidget

from opencae.ui.core.theme import PALETTE


class LabelRibbonGroup(QLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(str(text), parent)
        self.setObjectName("RibbonGroupTitle")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.refresh_theme()

    def refresh_theme(self) -> None:
        self.setStyleSheet(
            f"color:{PALETTE['accent']};"
            "font-size:8pt;"
            "font-weight:600;"
            "letter-spacing:1px;"
            "border:none;"
            "background:transparent;"
        )
