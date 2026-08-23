"""Provides the canonical OpenCAE combo box with a painted chevron."""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QPointF, QTimer, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QComboBox

from opencae.ui.core.theme import PALETTE
from opencae.ui.templates.control_metrics import (
    COMBO_POPUP_EXTRA_HEIGHT,
    COMBO_POPUP_ROW_HEIGHT,
    apply_primary_control_height,
)


class ChevronComboBox(QComboBox):
    """Canonical primary combo whose popup shows every entry when space permits."""

    def __init__(self, parent=None):
        """Initialize canonical 40 px geometry, flexible width and popup policy."""
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(0)
        apply_primary_control_height(self)
        self.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.setMinimumContentsLength(16)

    def showPopup(self) -> None:
        """Open the popup and explicitly size it to its complete item list.

        Some Qt platform styles ignore ``maxVisibleItems`` for non-editable
        combo boxes. The popup is therefore resized after Qt creates its view,
        using the same row-height token that the stylesheet uses for each item.
        """
        view = self.view()
        view.setMinimumHeight(0)
        view.setMaximumHeight(16_777_215)
        view.setSpacing(0)
        self.setMaxVisibleItems(max(1, self.count()))
        super().showPopup()

        # Native popup geometry may finish on the next event-loop turn. Fitting
        # twice prevents a platform style from reintroducing its default height.
        self._fit_popup_to_contents()
        QTimer.singleShot(0, self._fit_popup_to_contents)

    def _fit_popup_to_contents(self) -> None:
        """Resize the visible popup to complete rows without clipping its frame."""
        count = self.count()
        if count <= 0:
            return

        view = self.view()
        content_height = 2 * view.frameWidth() + COMBO_POPUP_EXTRA_HEIGHT
        for row in range(count):
            hinted = view.sizeHintForRow(row)
            content_height += max(COMBO_POPUP_ROW_HEIGHT, hinted if hinted > 0 else 0)

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

        # The popup frame/title chrome is outside the item view. Preserve it and
        # add the view's reserved bottom breathing room so the final row border
        # is never clipped by one or two pixels on native platform styles.
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
