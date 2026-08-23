"""Provides the canonical OpenCAE combo box with a painted chevron."""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QPointF, QTimer, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QComboBox

from opencae.ui.core.theme import PALETTE


class ChevronComboBox(QComboBox):
    """Flat combo box whose popup shows every entry when screen space permits."""

    def __init__(self, parent=None):
        """Initialize the canonical combo geometry and sizing policy."""
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(316)
        self.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.setMinimumContentsLength(16)

    def showPopup(self) -> None:
        """Open the popup and explicitly size it to its complete item list.

        Some Qt platform styles ignore ``maxVisibleItems`` for non-editable
        combo boxes and create a one-row popup with scroll arrows.  Resizing the
        actual popup view/container after Qt creates it makes the behavior
        independent of that style hint.
        """
        view = self.view()
        view.setMinimumHeight(0)
        view.setMaximumHeight(16_777_215)
        self.setMaxVisibleItems(max(1, self.count()))
        super().showPopup()

        # Qt may finish native popup geometry on the next event-loop turn, so
        # fit it both now and once more after that geometry has settled.
        self._fit_popup_to_contents()
        QTimer.singleShot(0, self._fit_popup_to_contents)

    def _fit_popup_to_contents(self) -> None:
        """Resize the visible popup to all rows, bounded by available screen."""
        count = self.count()
        if count <= 0:
            return

        view = self.view()
        fallback_row_height = max(self.fontMetrics().height() + 12, 28)
        content_height = 2 * view.frameWidth()
        for row in range(count):
            height = view.sizeHintForRow(row)
            content_height += height if height > 0 else fallback_row_height

        screen = self.screen()
        if screen is None:
            return
        available = screen.availableGeometry()
        top = self.mapToGlobal(QPoint(0, 0)).y()
        bottom = self.mapToGlobal(QPoint(0, self.height())).y()
        room_below = max(0, available.bottom() - bottom - 6)
        room_above = max(0, top - available.top() - 6)
        available_height = max(room_below, room_above)
        if available_height <= 0:
            return

        target_height = min(content_height, available_height)
        complete = target_height >= content_height
        view.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            if complete
            else Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        view.setMinimumHeight(target_height)
        view.setMaximumHeight(target_height)

        popup = view.window()
        if popup is None or popup is self.window():
            return
        chrome = max(0, popup.height() - view.height())
        popup_height = target_height + chrome
        popup.setMinimumHeight(popup_height)
        popup.setMaximumHeight(popup_height)
        popup.resize(max(popup.width(), self.width()), popup_height)

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
