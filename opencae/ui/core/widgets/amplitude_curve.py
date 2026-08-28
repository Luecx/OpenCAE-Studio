"""Lightweight themed scalar-curve preview used by amplitude editors."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from opencae.ui.core.theme import PALETTE


class AmplitudeCurvePreview(QWidget):
    """Render an amplitude polyline and its source knots without plot dependencies."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._points: list[tuple[float, float]] = []
        self._knots: list[tuple[float, float]] = []
        self.setMinimumSize(360, 280)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, points=(), knots=()) -> None:
        self._points = [(float(x), float(y)) for x, y in points]
        self._knots = [(float(x), float(y)) for x, y in knots]
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(PALETTE["panel_alt"]))

        outer = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        painter.setPen(QPen(QColor(PALETTE["border"]), 1.0))
        painter.drawRoundedRect(outer, 6.0, 6.0)

        title_height = 34.0
        left = 58.0
        right = 20.0
        bottom = 42.0
        plot = QRectF(
            left,
            title_height + 12.0,
            max(1.0, self.width() - left - right),
            max(1.0, self.height() - title_height - bottom - 18.0),
        )
        painter.setPen(QColor(PALETTE["text"]))
        painter.drawText(
            QRectF(0.0, 8.0, self.width(), 24.0),
            Qt.AlignmentFlag.AlignCenter,
            "Amplitude curve",
        )

        if len(self._points) < 2:
            painter.setPen(QColor(PALETTE["muted"]))
            painter.drawText(plot, Qt.AlignmentFlag.AlignCenter, "No valid curve data")
            painter.end()
            return

        xs = [point[0] for point in self._points]
        ys = [point[1] for point in self._points]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        if x_max == x_min:
            x_min -= 0.5
            x_max += 0.5
        if y_max == y_min:
            pad = max(0.5, abs(y_min) * 0.15)
            y_min -= pad
            y_max += pad
        else:
            pad = (y_max - y_min) * 0.08
            y_min -= pad
            y_max += pad

        grid_pen = QPen(QColor(PALETTE["border"]), 1.0, Qt.PenStyle.DotLine)
        axis_pen = QPen(QColor(PALETTE["muted"]), 1.0)
        painter.setFont(self.font())
        for index in range(6):
            fraction = index / 5.0
            x = plot.left() + fraction * plot.width()
            y = plot.bottom() - fraction * plot.height()
            painter.setPen(grid_pen)
            painter.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))

            painter.setPen(QColor(PALETTE["muted"]))
            x_value = x_min + fraction * (x_max - x_min)
            y_value = y_min + fraction * (y_max - y_min)
            painter.drawText(
                QRectF(x - 34.0, plot.bottom() + 5.0, 68.0, 20.0),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                _format_number(x_value),
            )
            painter.drawText(
                QRectF(2.0, y - 10.0, left - 8.0, 20.0),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                _format_number(y_value),
            )

        painter.setPen(axis_pen)
        painter.drawLine(plot.bottomLeft(), plot.bottomRight())
        painter.drawLine(plot.bottomLeft(), plot.topLeft())

        def mapped(point):
            x, y = point
            px = plot.left() + (x - x_min) / (x_max - x_min) * plot.width()
            py = plot.bottom() - (y - y_min) / (y_max - y_min) * plot.height()
            return QPointF(px, py)

        path = QPainterPath()
        path.moveTo(mapped(self._points[0]))
        for point in self._points[1:]:
            path.lineTo(mapped(point))
        painter.setPen(
            QPen(
                QColor(PALETTE["accent"]),
                2.0,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )
        painter.drawPath(path)

        painter.setPen(QPen(QColor(PALETTE["text"]), 1.0))
        painter.setBrush(QColor(PALETTE["accent"]))
        for point in self._knots:
            center = mapped(point)
            painter.drawEllipse(center, 3.5, 3.5)

        painter.setPen(QColor(PALETTE["muted"]))
        painter.drawText(
            QRectF(plot.left(), self.height() - 24.0, plot.width(), 18.0),
            Qt.AlignmentFlag.AlignCenter,
            "Time",
        )
        painter.save()
        painter.translate(15.0, plot.center().y())
        painter.rotate(-90.0)
        painter.drawText(
            QRectF(-plot.height() / 2.0, -10.0, plot.height(), 20.0),
            Qt.AlignmentFlag.AlignCenter,
            "Value",
        )
        painter.restore()
        painter.end()


def _format_number(value: float) -> str:
    magnitude = abs(value)
    if magnitude and (magnitude >= 1e4 or magnitude < 1e-3):
        return f"{value:.2e}"
    return f"{value:.3g}"
