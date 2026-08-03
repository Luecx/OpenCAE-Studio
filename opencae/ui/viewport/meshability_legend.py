from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from opencae.ui.core.theme import PALETTE
from .surface_shading import IRREGULAR_COLOR, REGULAR_COLOR


class MeshabilityLegend(QFrame):
    """Compact geometry meshability key styled like the result info panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MeshabilityLegend")
        self.setStyleSheet(
            f"QFrame#MeshabilityLegend{{"
            f"background:{PALETTE['panel']};"
            f"border:1px solid {PALETTE['border_light']};"
            "border-radius:7px;"
            "}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(12)
        layout.addWidget(self._entry("Regular", REGULAR_COLOR))
        layout.addWidget(self._entry("Irregular", IRREGULAR_COLOR))
        self.adjustSize()
        self.hide()

    @staticmethod
    def _entry(text: str, color: str) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        swatch = QLabel()
        swatch.setFixedSize(9, 9)
        swatch.setStyleSheet(
            f"background:{color};"
            f"border:1px solid {PALETTE['border_light']};"
            "border-radius:2px;"
        )

        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        label.setStyleSheet(f"color:{PALETTE['muted']};font-size:8pt;")
        layout.addWidget(swatch)
        layout.addWidget(label)
        return container
