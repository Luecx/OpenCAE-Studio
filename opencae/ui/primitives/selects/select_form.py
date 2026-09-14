"""Canonical primary form select with shared chevron and popup behavior."""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QPointF, QTimer, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QComboBox, QWidget

from opencae.ui.primitives.inputs.geometry import apply_primary_input_geometry

_POPUP_ROW_HEIGHT = 24
_POPUP_EXTRA_HEIGHT = 8
_CHEVRON_HALF_WIDTH = 6
_CHEVRON_HALF_HEIGHT = 3


class SelectForm(QComboBox):
    """Canonical primary-height select used by forms and reusable composites."""

    def __init__(
        self,
        items=(),
        *,
        current=None,
        object_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if object_name:
            self.setObjectName(object_name)
        apply_primary_input_geometry(self)
        if items:
            self.addItems(tuple(str(item) for item in items))
        if current is not None:
            self.setCurrentText(str(current))

    def showPopup(self) -> None:
        view = self.view()
        count = self.count()
        if count:
            visible_rows = min(count, 20)
            view.setMinimumHeight(
                visible_rows * _POPUP_ROW_HEIGHT + _POPUP_EXTRA_HEIGHT
            )
            view.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
                if count > visible_rows
                else Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
        super().showPopup()
        QTimer.singleShot(0, self._match_popup_width)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        rect = self.rect()
        center_x = rect.right() - 12
        center_y = rect.center().y()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(self._chevron_color(), 1.5))
        points = (
            QPointF(
                center_x - _CHEVRON_HALF_WIDTH,
                center_y - _CHEVRON_HALF_HEIGHT,
            ),
            QPointF(center_x, center_y + _CHEVRON_HALF_HEIGHT),
            QPointF(
                center_x + _CHEVRON_HALF_WIDTH,
                center_y - _CHEVRON_HALF_HEIGHT,
            ),
        )
        painter.drawPolyline(*points)
        painter.end()

    def _chevron_color(self) -> QColor:
        palette = self.palette()
        return QColor(
            palette.color(
                palette.ColorGroup.Disabled
                if not self.isEnabled()
                else palette.ColorGroup.Active,
                palette.ColorRole.Text,
            )
        )

    def _match_popup_width(self) -> None:
        view = self.view()
        window = view.window()
        if window is None:
            return
        desired_width = max(self.width(), view.sizeHintForColumn(0) + 32)
        global_pos = self.mapToGlobal(QPoint(0, self.height()))
        screen = self.screen()
        if screen is not None:
            available = screen.availableGeometry()
            desired_width = min(desired_width, available.width())
            global_pos.setX(
                min(
                    max(global_pos.x(), available.left()),
                    available.right() - desired_width + 1,
                )
            )
        window.resize(desired_width, window.height())
        window.move(global_pos)
