"""Accent group title shown below expanded ribbon actions."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QWidget


class LabelRibbonGroup(QLabel):
    """Canonical ribbon-group caption styled exclusively by the global theme."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(str(text), parent)
        self.setObjectName("RibbonGroupTitle")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def refresh_theme(self) -> None:
        """Re-polish after a global stylesheet change without importing theme state."""
        style = self.style()
        style.unpolish(self)
        style.polish(self)
        self.update()
