from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from opencae.ui.core.theme import PALETTE


class MeshabilityLegend(QFrame):
    """Compact geometry meshability key styled like the result info panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MeshabilityLegend")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(12)
        self._regular = self._entry("Regular", "meshability_regular")
        self._irregular = self._entry("Irregular", "meshability_irregular")
        layout.addWidget(self._regular)
        layout.addWidget(self._irregular)
        self.refresh_theme()
        self.adjustSize()
        self.hide()

    def paintEvent(self, event) -> None:
        """Paint a rounded panel over a viewport-colored rectangular backing."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(PALETTE["viewport"]))
        painter.setBrush(QColor(PALETTE["overlay_bg"]))
        painter.setPen(QPen(QColor(PALETTE["overlay_border"]), 1.0))
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.drawRoundedRect(rect, 7.0, 7.0)

    def _entry(self, text: str, token: str) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        swatch = QLabel()
        swatch.setObjectName("MeshabilitySwatch")
        swatch.setProperty("colorToken", token)
        swatch.setFixedSize(9, 9)

        label = QLabel(text)
        label.setObjectName("MeshabilityLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(swatch)
        layout.addWidget(label)
        return container

    def refresh_theme(self) -> None:
        """Refresh local swatches whose colors are not expressible as global QSS."""
        self.setStyleSheet(
            f"QLabel#MeshabilityLabel{{color:{PALETTE['muted']};font-size:8pt;}}"
        )
        for container in (self._regular, self._irregular):
            swatch = container.findChild(QLabel, "MeshabilitySwatch")
            if swatch is None:
                continue
            token = str(swatch.property("colorToken") or "")
            color = PALETTE.get(token, PALETTE["cad_face"])
            swatch.setStyleSheet(
                f"background:{color};"
                f"border:1px solid {PALETTE['overlay_border']};"
                "border-radius:2px;"
            )
        self.update()
