from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from opencae.ui.core.theme import PALETTE


class ResultRibbonGroup(QFrame):
    def __init__(self, title, widgets=(), parent=None):
        super().__init__(parent)
        self.setObjectName("RibbonGroup")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(
            f"QFrame#RibbonGroup {{ background: rgba(255,255,255,0.012); "
            f"border-right: 1px solid {PALETTE['border_light']}; }}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 9, 2)
        layout.setSpacing(1)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(2)
        for widget in widgets:
            row.addWidget(widget)
        layout.addLayout(row)
        label = QLabel(title)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            f"color:{PALETTE['accent']};font-size:8pt;font-weight:600;"
            "letter-spacing:1px;border:none;background:transparent;"
        )
        layout.addWidget(label)
