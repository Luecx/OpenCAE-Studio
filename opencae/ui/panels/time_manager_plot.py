"""Draw the interactive frame/time curve used by the Time Manager."""

from __future__ import annotations

from math import isfinite

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QToolTip, QWidget

from opencae.ui.core.theme import PALETTE


class TimeManagerPlot(QWidget):
    """Render a compact clickable frame curve without an external chart dependency."""

    frame_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._x = []
        self._y = []
        self._current_index = -1
        self._cursor_x = None
        self._x_label = "Frame"
        self._y_label = "Value"
        self._screen_points = []
        self.setMouseTracking(True)
        self.setMinimumHeight(150)
        self.setObjectName("TimeManagerPlot")

    def set_series(
        self,
        x_values,
        y_values,
        *,
        current_index=-1,
        cursor_x=None,
        x_label="Frame",
        y_label="Value",
    ) -> None:
        """Replace the plotted frame series and current-playhead state."""
        pairs = [
            (float(x), float(y))
            for x, y in zip(tuple(x_values), tuple(y_values))
            if isfinite(float(x)) and isfinite(float(y))
        ]
        self._x = [pair[0] for pair in pairs]
        self._y = [pair[1] for pair in pairs]
        self._current_index = int(current_index)
        self._cursor_x = None if cursor_x is None else float(cursor_x)
        self._x_label = str(x_label)
        self._y_label = str(y_label)
        self.update()

    def set_current_index(self, index: int) -> None:
        self._current_index = int(index)
        self.update()

    def set_cursor_x(self, value) -> None:
        self._cursor_x = None if value is None else float(value)
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(PALETTE["panel"]))

        plot = QRectF(self.rect()).adjusted(64.0, 20.0, -22.0, -42.0)
        if plot.width() <= 10 or plot.height() <= 10:
            return
        painter.setPen(QPen(QColor(PALETTE["border_light"]), 1.0))
        painter.drawRoundedRect(plot, 4.0, 4.0)

        if not self._x:
            painter.setPen(QColor(PALETTE["muted"]))
            painter.drawText(plot, Qt.AlignmentFlag.AlignCenter, "No result frames")
            self._screen_points = []
            return

        x_min, x_max = min(self._x), max(self._x)
        y_min, y_max = min(self._y), max(self._y)
        if abs(x_max - x_min) <= 1.0e-14:
            x_max = x_min + 1.0
        if abs(y_max - y_min) <= 1.0e-14:
            y_max = y_min + max(abs(y_min), 1.0)
        if y_min >= 0.0:
            y_min = 0.0
        y_span = y_max - y_min
        y_max += 0.04 * y_span

        def point(x, y):
            px = plot.left() + (x - x_min) / (x_max - x_min) * plot.width()
            py = plot.bottom() - (y - y_min) / (y_max - y_min) * plot.height()
            return QPointF(px, py)

        grid_pen = QPen(QColor(PALETTE["border"]), 1.0, Qt.PenStyle.DotLine)
        text_color = QColor(PALETTE["muted"])
        painter.setPen(grid_pen)
        for index in range(5):
            fraction = index / 4.0
            y = plot.bottom() - fraction * plot.height()
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            value = y_min + fraction * (y_max - y_min)
            painter.setPen(text_color)
            painter.drawText(
                QRectF(4.0, y - 9.0, 54.0, 18.0),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                f"{value:.3g}",
            )
            painter.setPen(grid_pen)

        x_ticks = tuple(dict.fromkeys(self._x))
        if len(x_ticks) > 7:
            stride = max(1, (len(x_ticks) - 1) // 5)
            x_ticks = tuple(x_ticks[::stride])
            if x_ticks[-1] != self._x[-1]:
                x_ticks = (*x_ticks, self._x[-1])
        for value in x_ticks:
            px = point(value, y_min).x()
            painter.setPen(grid_pen)
            painter.drawLine(QPointF(px, plot.top()), QPointF(px, plot.bottom()))
            painter.setPen(text_color)
            label = (
                str(int(round(value)))
                if abs(value - round(value)) <= 1.0e-9
                else f"{value:.4g}"
            )
            painter.drawText(
                QRectF(px - 34.0, plot.bottom() + 5.0, 68.0, 18.0),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                label,
            )

        painter.setPen(QColor(PALETTE["muted"]))
        painter.drawText(
            QRectF(plot.left(), plot.bottom() + 23.0, plot.width(), 18.0),
            Qt.AlignmentFlag.AlignCenter,
            self._x_label,
        )
        painter.drawText(
            QRectF(plot.left() + 8.0, plot.top() + 4.0, 120.0, 18.0),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            self._y_label,
        )

        screen_points = [point(x, y) for x, y in zip(self._x, self._y)]
        self._screen_points = screen_points
        path = QPainterPath(screen_points[0])
        for value in screen_points[1:]:
            path.lineTo(value)
        painter.setPen(QPen(QColor(PALETTE["accent"]), 2.0))
        painter.drawPath(path)

        if self._cursor_x is not None and x_min <= self._cursor_x <= x_max:
            px = point(self._cursor_x, y_min).x()
            painter.setPen(QPen(QColor(PALETTE["accent_hover"]), 1.0, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(px, plot.top()), QPointF(px, plot.bottom()))

        for index, screen in enumerate(screen_points):
            selected = index == self._current_index
            radius = 6.0 if selected else 4.0
            painter.setPen(QPen(QColor(PALETTE["text"]), 1.0))
            painter.setBrush(QColor(PALETTE["accent"] if selected else PALETTE["panel_alt"]))
            painter.drawEllipse(screen, radius, radius)
            if selected:
                painter.setPen(QPen(QColor(PALETTE["accent_hover"]), 2.0))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(screen, radius + 3.0, radius + 3.0)

    def _nearest_marker(self, position, tolerance=10.0):
        if not self._screen_points:
            return None
        px, py = float(position.x()), float(position.y())
        distances = [
            (point.x() - px) ** 2 + (point.y() - py) ** 2
            for point in self._screen_points
        ]
        index = min(range(len(distances)), key=distances.__getitem__)
        return index if distances[index] <= tolerance * tolerance else None

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            index = self._nearest_marker(event.position())
            if index is not None:
                self.frame_selected.emit(index)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        index = self._nearest_marker(event.position())
        if index is None:
            QToolTip.hideText()
        else:
            QToolTip.showText(
                event.globalPosition().toPoint(),
                f"Frame: {index + 1}\n{self._y_label}: {self._y[index]:.6g}",
                self,
            )
        super().mouseMoveEvent(event)
