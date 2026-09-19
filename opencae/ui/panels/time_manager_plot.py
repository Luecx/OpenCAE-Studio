"""Draw the interactive frame/time curve used by the Time Manager."""

from __future__ import annotations

from math import isfinite

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QCursor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QToolTip, QWidget

from opencae.ui.core.theme import PALETTE


class TimeManagerPlot(QWidget):
    """Render a compact frame/value curve with draggable playback boundaries."""

    frame_selected = pyqtSignal(int)
    play_range_changed = pyqtSignal(float, float)

    HANDLE_TOLERANCE = 9.0
    MIN_RANGE_PIXELS = 3.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._x = []
        self._y = []
        self._current_index = -1
        self._cursor_x = None
        self._x_label = "Time"
        self._y_label = "Value"
        self._show_markers = True
        self._interactive = True
        self._screen_points = []
        self._play_start = None
        self._play_end = None
        self._range_editable = True
        self._drag_boundary = None
        self.setMouseTracking(True)
        self.setMinimumHeight(130)
        self.setObjectName("TimeManagerPlot")

    def set_series(
        self,
        x_values,
        y_values,
        *,
        current_index=-1,
        cursor_x=None,
        x_label="Time",
        y_label="Value",
        show_markers=True,
        interactive=True,
        play_start=None,
        play_end=None,
        range_editable=True,
        show_play_range=True,
    ) -> None:
        """Replace the plotted series, playhead, and playback-boundary state."""
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
        self._show_markers = bool(show_markers)
        self._interactive = bool(interactive)
        self._screen_points = []
        self._range_editable = bool(range_editable)
        self._drag_boundary = None
        if self._x and show_play_range:
            x_min, x_max = min(self._x), max(self._x)
            start = x_min if play_start is None else float(play_start)
            end = x_max if play_end is None else float(play_end)
            self._play_start, self._play_end = self._bounded_play_range(start, end)
        else:
            self._play_start = None
            self._play_end = None
        self.update()

    def set_current_index(self, index: int) -> None:
        self._current_index = int(index)
        self.update()

    def set_cursor_x(self, value) -> None:
        self._cursor_x = None if value is None else float(value)
        self.update()

    def set_play_range(self, start, end) -> None:
        """Move both playback boundaries without replacing the plotted series."""
        if not self._x:
            return
        self._play_start, self._play_end = self._bounded_play_range(start, end)
        self.update()

    def _plot_rect(self) -> QRectF:
        return QRectF(self.rect()).adjusted(56.0, 8.0, -12.0, -28.0)

    def _x_domain(self):
        if not self._x:
            return None
        x_min, x_max = min(self._x), max(self._x)
        if abs(x_max - x_min) <= 1.0e-14:
            x_max = x_min + 1.0
        return x_min, x_max

    def _minimum_range_span(self) -> float:
        """Keep handles visibly separate so either boundary can always be grabbed."""
        domain = self._x_domain()
        if domain is None:
            return 0.0
        x_min, x_max = domain
        span = max(x_max - x_min, 0.0)
        if span <= 1.0e-14:
            return 0.0
        width = max(float(self._plot_rect().width()), 1.0)
        return min(
            span,
            max(span * 1.0e-6, span * self.MIN_RANGE_PIXELS / width),
        )

    def _bounded_play_range(self, start, end):
        """Clamp a range to the plot domain while preventing coincident handles."""
        domain = self._x_domain()
        if domain is None:
            return None, None
        x_min, x_max = domain
        first = min(max(float(start), x_min), x_max)
        second = min(max(float(end), first), x_max)
        minimum = self._minimum_range_span()
        if second - first < minimum:
            if first + minimum <= x_max:
                second = first + minimum
            else:
                first = max(x_min, second - minimum)
        return first, second

    def _screen_x(self, value: float) -> float:
        domain = self._x_domain()
        plot = self._plot_rect()
        if domain is None or plot.width() <= 0.0:
            return plot.left()
        x_min, x_max = domain
        return plot.left() + (float(value) - x_min) / (x_max - x_min) * plot.width()

    def _value_at_screen_x(self, px: float) -> float:
        domain = self._x_domain()
        plot = self._plot_rect()
        if domain is None or plot.width() <= 0.0:
            return 0.0
        x_min, x_max = domain
        fraction = (float(px) - plot.left()) / plot.width()
        fraction = min(max(fraction, 0.0), 1.0)
        return x_min + fraction * (x_max - x_min)

    def _nearest_boundary(self, position):
        if (
            not self._range_editable
            or self._play_start is None
            or self._play_end is None
        ):
            return None
        px = float(position.x())
        distances = {
            "start": abs(px - self._screen_x(self._play_start)),
            "end": abs(px - self._screen_x(self._play_end)),
        }
        boundary = min(distances, key=distances.get)
        return boundary if distances[boundary] <= self.HANDLE_TOLERANCE else None

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(PALETTE["panel"]))

        # Use almost the complete vertical workspace. Only reserve the compact
        # tick/axis text strips that are actually needed.
        plot = self._plot_rect()
        if plot.width() <= 10 or plot.height() <= 10:
            return
        painter.setPen(QPen(QColor(PALETTE["border_light"]), 1.0))
        painter.drawRoundedRect(plot, 4.0, 4.0)

        if not self._x:
            painter.setPen(QColor(PALETTE["muted"]))
            painter.drawText(plot, Qt.AlignmentFlag.AlignCenter, "No result frames")
            self._screen_points = []
            return

        x_min, x_max = self._x_domain()
        y_min, y_max = min(self._y), max(self._y)
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
                QRectF(2.0, y - 8.0, 48.0, 16.0),
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
                QRectF(px - 32.0, plot.bottom() + 2.0, 64.0, 15.0),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                label,
            )

        painter.setPen(QColor(PALETTE["muted"]))
        painter.drawText(
            QRectF(plot.left(), plot.bottom() + 14.0, plot.width(), 13.0),
            Qt.AlignmentFlag.AlignCenter,
            self._x_label,
        )
        painter.drawText(
            QRectF(plot.left() + 7.0, plot.top() + 3.0, 150.0, 15.0),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            self._y_label,
        )

        screen_points = [point(x, y) for x, y in zip(self._x, self._y)]
        self._screen_points = screen_points if self._interactive else []
        path = QPainterPath(screen_points[0])
        for value in screen_points[1:]:
            path.lineTo(value)
        painter.setPen(QPen(QColor(PALETTE["accent"]), 2.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        # Playback limits are intentionally distinct from the blue playhead:
        # dashed red lines remain visible at rest and can be dragged horizontally.
        if self._play_start is not None and self._play_end is not None:
            range_pen = QPen(QColor(PALETTE["danger"]), 1.5, Qt.PenStyle.DashLine)
            painter.setPen(range_pen)
            for value in (self._play_start, self._play_end):
                px = self._screen_x(value)
                painter.drawLine(QPointF(px, plot.top()), QPointF(px, plot.bottom()))

        if self._cursor_x is not None and x_min <= self._cursor_x <= x_max:
            px = point(self._cursor_x, y_min).x()
            painter.setPen(
                QPen(QColor(PALETTE["accent_hover"]), 1.0, Qt.PenStyle.DashLine)
            )
            painter.drawLine(QPointF(px, plot.top()), QPointF(px, plot.bottom()))

        if self._show_markers:
            for index, screen in enumerate(screen_points):
                selected = index == self._current_index
                radius = 6.0 if selected else 4.0
                painter.setPen(QPen(QColor(PALETTE["text"]), 1.0))
                painter.setBrush(
                    QColor(PALETTE["accent"] if selected else PALETTE["panel_alt"])
                )
                painter.drawEllipse(screen, radius, radius)
                if selected:
                    painter.setPen(QPen(QColor(PALETTE["accent_hover"]), 2.0))
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawEllipse(screen, radius + 3.0, radius + 3.0)

    def _nearest_marker(self, position, tolerance=10.0):
        if not self._interactive or not self._screen_points:
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
            boundary = self._nearest_boundary(event.position())
            if boundary is not None:
                self._drag_boundary = boundary
                self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
                event.accept()
                return
            index = self._nearest_marker(event.position())
            if index is not None:
                self.frame_selected.emit(index)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_boundary is not None:
            value = self._value_at_screen_x(event.position().x())
            minimum = self._minimum_range_span()
            domain = self._x_domain()
            if self._drag_boundary == "start":
                value = min(value, float(self._play_end) - minimum)
                self._play_start = max(float(domain[0]), value)
            else:
                value = max(value, float(self._play_start) + minimum)
                self._play_end = min(float(domain[1]), value)
            self.play_range_changed.emit(float(self._play_start), float(self._play_end))
            self.update()
            event.accept()
            return

        boundary = self._nearest_boundary(event.position())
        self.setCursor(
            QCursor(Qt.CursorShape.SizeHorCursor)
            if boundary is not None
            else QCursor(Qt.CursorShape.ArrowCursor)
        )
        index = self._nearest_marker(event.position())
        if boundary is not None:
            value = self._play_start if boundary == "start" else self._play_end
            QToolTip.showText(
                event.globalPosition().toPoint(),
                f"Play {boundary}: {float(value):.6g}",
                self,
            )
        elif index is None:
            QToolTip.hideText()
        else:
            QToolTip.showText(
                event.globalPosition().toPoint(),
                f"Frame: {index + 1}\n"
                f"{self._x_label}: {self._x[index]:.6g}\n"
                f"{self._y_label}: {self._y[index]:.6g}",
                self,
            )
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._drag_boundary is not None:
            self._drag_boundary = None
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)
