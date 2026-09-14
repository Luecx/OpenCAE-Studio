"""Sketcher-specific canvas polish layered on the reusable drafting surface."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QFont, QPainter, QPen

from .canvas import SketchCanvas, _EPS, _theme


class SketchEditorCanvas(SketchCanvas):
    """Use screen-stable labels and CAD-style construction editing in the dialog."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # QGraphicsView keeps hidden scroll ranges for panning, so disabling the
        # chrome does not remove middle-mouse navigation.
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def set_construction(self, enabled: bool) -> None:
        """Apply construction state to selected entities as well as new geometry."""
        enabled = bool(enabled)
        selected = tuple(self.selected_entities())
        changed = tuple(
            entity
            for entity in selected
            if bool(getattr(entity, "construction", False)) != enabled
        )
        self.construction = enabled
        if changed:
            self._push_history()
            for entity in changed:
                entity.construction = enabled
            self._changed(solve=False)
        else:
            self.viewport().update()

    def _draw_axes(self, painter: QPainter, rect, major: float) -> None:
        """Draw axes in scene space but labels at a fixed, restrained screen size."""
        painter.save()
        x_pen = QPen(_theme("axis_x", "#de6a62"))
        y_pen = QPen(_theme("axis_y", "#66b56f"))
        x_pen.setCosmetic(True)
        y_pen.setCosmetic(True)
        x_pen.setWidthF(1.6 if self.show_revolve_axis else 1.15)
        y_pen.setWidthF(1.15)
        if self.show_revolve_axis:
            x_pen.setStyle(Qt.PenStyle.DashDotLine)
        painter.setPen(x_pen)
        painter.drawLine(QPointF(rect.left(), 0.0), QPointF(rect.right(), 0.0))
        painter.setPen(y_pen)
        painter.drawLine(QPointF(0.0, rect.top()), QPointF(0.0, rect.bottom()))
        painter.restore()

        painter.save()
        painter.resetTransform()
        text_color = _theme("muted", "#98a2ad")
        text_color.setAlpha(175)
        text_pen = QPen(text_color)
        text_pen.setCosmetic(True)
        painter.setPen(text_pen)
        font = QFont(painter.font())
        font.setPixelSize(10)
        font.setWeight(QFont.Weight.Normal)
        painter.setFont(font)

        viewport = self.viewport().rect()
        x_axis_y = self.mapFromScene(QPointF(0.0, 0.0)).y()
        y_axis_x = self.mapFromScene(QPointF(0.0, 0.0)).x()

        for index in range(int(rect.left() // major) - 1, int(rect.right() // major) + 2):
            if not index:
                continue
            value = index * major
            screen = self.mapFromScene(QPointF(value, 0.0))
            if -40 <= screen.x() <= viewport.width() + 40:
                painter.drawText(screen.x() + 4, x_axis_y - 4, f"{value:g}")

        model_min_y = -rect.bottom()
        model_max_y = -rect.top()
        for index in range(int(model_min_y // major) - 1, int(model_max_y // major) + 2):
            if not index:
                continue
            value = index * major
            screen = self.mapFromScene(QPointF(0.0, -value))
            if -20 <= screen.y() <= viewport.height() + 20:
                painter.drawText(y_axis_x + 5, screen.y() - 3, f"{value:g}")

        if self.show_revolve_axis:
            axis_color = _theme("axis_x", "#de6a62")
            axis_color.setAlpha(190)
            painter.setPen(QPen(axis_color))
            painter.drawText(10, max(13, x_axis_y - 7), "REVOLVE AXIS  X")
        painter.restore()


__all__ = ["SketchEditorCanvas"]
