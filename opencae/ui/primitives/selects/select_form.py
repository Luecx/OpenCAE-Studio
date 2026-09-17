"""Canonical primary form select with shared chevron and popup behavior."""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QPointF, QTimer, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QComboBox, QWidget

from opencae.ui.foundation.metrics import COMBO_POPUP_EXTRA_HEIGHT, COMBO_POPUP_ROW_HEIGHT
from opencae.ui.foundation.theme import PALETTE
from opencae.ui.primitives.inputs.geometry import apply_primary_input_geometry


class SelectForm(QComboBox):
    """Canonical primary combo whose popup shows complete rows when possible."""

    def __init__(
        self,
        items=(),
        *,
        current=None,
        object_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        # Preserve normal Qt construction syntax (SelectForm(parent)) while also
        # allowing an optional iterable of initial display strings.
        if isinstance(items, QWidget) and parent is None:
            parent = items
            items = ()
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(0)
        apply_primary_input_geometry(self)
        self.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.setMinimumContentsLength(16)
        if object_name:
            self.setObjectName(object_name)
        if items:
            self.addItems(tuple(str(item) for item in items))
        if current is not None:
            self.setCurrentText(str(current))

    def showPopup(self) -> None:
        """Open the popup sized to complete rows instead of native defaults."""
        view = self.view()
        view.setMinimumHeight(0)
        view.setMaximumHeight(16_777_215)
        view.setSpacing(0)
        self.setMaxVisibleItems(max(1, self.count()))
        super().showPopup()
        self._fit_popup_to_contents()
        QTimer.singleShot(0, self._fit_popup_to_contents)

    def _fit_popup_to_contents(self) -> None:
        count = self.count()
        if count <= 0:
            return

        view = self.view()
        content_height = 2 * view.frameWidth() + COMBO_POPUP_EXTRA_HEIGHT
        for row in range(count):
            hinted = view.sizeHintForRow(row)
            content_height += max(
                COMBO_POPUP_ROW_HEIGHT,
                hinted if hinted > 0 else 0,
            )

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
