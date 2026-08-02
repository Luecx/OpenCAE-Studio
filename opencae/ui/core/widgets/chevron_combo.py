from __future__ import annotations

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QComboBox

from opencae.ui.core.theme import PALETTE


class ChevronComboBox(QComboBox):
    """Flat combo box with an always-visible disclosure chevron."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(316)
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(16)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        color = PALETTE["accent"] if self.hasFocus() else PALETTE["muted"]
        painter.setPen(QPen(QColor(color), 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        x = self.width() - 14.0
        y = self.height() / 2.0 - 1.0
        painter.drawLine(QPointF(x - 4.0, y - 2.0), QPointF(x, y + 2.0))
        painter.drawLine(QPointF(x, y + 2.0), QPointF(x + 4.0, y - 2.0))
        painter.end()
