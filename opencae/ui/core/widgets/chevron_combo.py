"""Provides the canonical OpenCAE combo box with a painted chevron."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QComboBox

from opencae.ui.core.theme import PALETTE


class ChevronComboBox(QComboBox):
    """Flat combo box with an always-visible disclosure chevron.

    The popup requests enough rows for the complete model. Qt still constrains
    the popup to the available screen geometry, so scrolling only appears when
    the screen genuinely cannot fit every entry.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(316)
        self.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.setMinimumContentsLength(16)

    def showPopup(self) -> None:
        """Request one visible popup row per entry before opening the menu."""
        self.setMaxVisibleItems(max(1, self.count()))
        self.view().setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        super().showPopup()

    def paintEvent(self, event) -> None:
        """Paint the normal combo contents plus the OpenCAE disclosure mark."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        color = PALETTE["accent"] if self.hasFocus() else PALETTE["muted"]
        painter.setPen(
            QPen(
                QColor(color),
                1.7,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
            )
        )
        x = self.width() - 14.0
        y = self.height() / 2.0 - 1.0
        painter.drawLine(QPointF(x - 4.0, y - 2.0), QPointF(x, y + 2.0))
        painter.drawLine(QPointF(x, y + 2.0), QPointF(x + 4.0, y - 2.0))
        painter.end()
