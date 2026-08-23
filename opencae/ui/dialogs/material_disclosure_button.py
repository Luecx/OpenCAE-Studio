"""Provides the compact painted disclosure control used by material cards."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QToolButton

from opencae.ui.core.theme import PALETTE


class MaterialDisclosureButton(QToolButton):
    """Draw a consistent up/down chevron without relying on font glyphs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._expanded = False
        self.setObjectName("MaterialBehaviorChevron")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_expanded(self, expanded: bool) -> None:
        """Set the visual disclosure direction and schedule a repaint."""
        self._expanded = bool(expanded)
        self.update()

    def paintEvent(self, event) -> None:
        """Paint the normal tool button chrome followed by a centered chevron."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        color = PALETTE["muted"] if self.isEnabled() else PALETTE["border_light"]
        if self.underMouse() and self.isEnabled():
            color = PALETTE["text"]
        painter.setPen(
            QPen(
                QColor(color),
                1.6,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )
        x = self.width() / 2.0
        y = self.height() / 2.0
        direction = -1.0 if self._expanded else 1.0
        painter.drawLine(QPointF(x - 4.0, y - 2.0 * direction), QPointF(x, y + 2.0 * direction))
        painter.drawLine(QPointF(x, y + 2.0 * direction), QPointF(x + 4.0, y - 2.0 * direction))
        painter.end()
