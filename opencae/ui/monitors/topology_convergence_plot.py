"""Paints topology objective and constraint histories without chart dependencies."""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QFontMetricsF, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from opencae.ui.core.theme import PALETTE


class TopologyConvergencePlot(QWidget):
    """Render iteration history with objective-left and constraint-right axes."""

    def __init__(self, parent=None):
        """Create an empty responsive convergence plot."""
        super().__init__(parent)
        self._iterations = ()
        self._constraint_limit: float | None = None
        self.setMinimumSize(360, 240)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

    def sizeHint(self) -> QSize:
        """Return a comfortable default plot size for the monitor tab."""
        return QSize(760, 460)

    def set_iterations(self, iterations, constraint_limit=None) -> None:
        """Replace the displayed history and optional constraint-limit guide."""
        self._iterations = tuple(iterations)
        self._constraint_limit = (
            float(constraint_limit) if constraint_limit is not None else None
        )
        self.update()

    def paintEvent(self, _event) -> None:
        """Paint axes, grid, legends and both convergence polylines."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(PALETTE["panel"]))
        plot = QRectF(70.0, 46.0, self.width() - 140.0, self.height() - 104.0)
        if plot.width() < 80.0 or plot.height() < 80.0:
            return

        samples = self._samples()
        if not samples:
            painter.setPen(QColor(PALETTE["muted"]))
            painter.drawText(
                plot,
                Qt.AlignmentFlag.AlignCenter,
                "Waiting for optimization iterations",
            )
            return

        numbers, objectives, constraints = zip(*samples)
        objective_range = _axis_range(objectives)
        constraint_range = _axis_range(
            (*constraints, self._constraint_limit)
            if self._constraint_limit is not None
            else constraints
        )
        self._draw_grid(
            painter,
            plot,
            numbers,
            objective_range,
            constraint_range,
        )
        self._draw_limit(painter, plot, constraint_range)
        self._draw_series(
            painter,
            plot,
            numbers,
            objectives,
            objective_range,
            QColor(PALETTE["accent"]),
        )
        self._draw_series(
            painter,
            plot,
            numbers,
            constraints,
            constraint_range,
            QColor(PALETTE["warning"]),
        )
        self._draw_legend(painter, plot)

    def _samples(self) -> list[tuple[int, float, float]]:
        """Return finite iteration, objective and first-constraint samples."""
        result = []
        for iteration in self._iterations:
            constraints = tuple(dict(iteration.constraint_values).values())
            if not constraints:
                continue
            objective = float(iteration.objective_value)
            constraint = float(constraints[0])
            if math.isfinite(objective) and math.isfinite(constraint):
                result.append((int(iteration.number), objective, constraint))
        return result

    def _draw_grid(
        self,
        painter,
        plot,
        numbers,
        objective_range,
        constraint_range,
    ) -> None:
        """Draw plot frame, shared iteration axis, and two value axes."""
        painter.setPen(QPen(QColor(PALETTE["border"]), 1.0))
        for index in range(5):
            fraction = index / 4.0
            y = plot.bottom() - fraction * plot.height()
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            objective = _interpolate(objective_range, fraction)
            constraint = _interpolate(constraint_range, fraction)
            painter.setPen(QColor(PALETTE["muted"]))
            painter.drawText(
                QRectF(0.0, y - 10.0, plot.left() - 8.0, 20.0),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                f"{objective:.4g}",
            )
            painter.drawText(
                QRectF(plot.right() + 8.0, y - 10.0, 62.0, 20.0),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"{constraint:.4g}",
            )
            painter.setPen(QPen(QColor(PALETTE["border"]), 1.0))
        painter.drawRect(plot)
        for number in _iteration_ticks(numbers):
            x = _map_x(number, numbers, plot)
            painter.setPen(QColor(PALETTE["muted"]))
            painter.drawText(
                QRectF(x - 28.0, plot.bottom() + 8.0, 56.0, 20.0),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                str(number),
            )
        painter.drawText(
            QRectF(plot.left(), plot.bottom() + 31.0, plot.width(), 20.0),
            Qt.AlignmentFlag.AlignCenter,
            "Iteration",
        )

    def _draw_series(self, painter, plot, numbers, values, value_range, color):
        """Draw one colored polyline and its iteration sample points."""
        points = [
            QPointF(
                _map_x(number, numbers, plot),
                _map_y(value, value_range, plot),
            )
            for number, value in zip(numbers, values, strict=True)
        ]
        path = QPainterPath(points[0])
        for point in points[1:]:
            path.lineTo(point)
        painter.setPen(QPen(color, 2.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        painter.setBrush(color)
        for point in points:
            painter.drawEllipse(point, 3.0, 3.0)

    def _draw_limit(self, painter, plot, constraint_range) -> None:
        """Draw the active constraint limit as a dashed right-axis guide."""
        if self._constraint_limit is None:
            return
        y = _map_y(self._constraint_limit, constraint_range, plot)
        pen = QPen(QColor(PALETTE["warning"]), 1.0, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))

    def _draw_legend(self, painter, plot) -> None:
        """Draw axis ownership and line colors above the plot."""
        entries = (
            ("Objective · left axis", PALETTE["accent"]),
            ("Constraint · right axis", PALETTE["warning"]),
        )
        x = plot.left()
        metrics = QFontMetricsF(painter.font())
        for label, color in entries:
            painter.setPen(QPen(QColor(color), 2.0))
            painter.drawLine(QPointF(x, 24.0), QPointF(x + 22.0, 24.0))
            painter.setPen(QColor(PALETTE["text"]))
            painter.drawText(QPointF(x + 29.0, 29.0), label)
            x += 43.0 + metrics.horizontalAdvance(label)


def _axis_range(values) -> tuple[float, float]:
    """Return a padded finite plotting interval containing all supplied values."""
    finite = [
        float(value)
        for value in values
        if value is not None and math.isfinite(float(value))
    ]
    if not finite:
        return 0.0, 1.0
    minimum, maximum = min(finite), max(finite)
    if minimum == maximum:
        padding = max(abs(minimum) * 0.08, 1.0e-6)
    else:
        padding = (maximum - minimum) * 0.08
    return minimum - padding, maximum + padding


def _interpolate(bounds, fraction) -> float:
    """Interpolate one normalized fraction inside an axis interval."""
    return bounds[0] + float(fraction) * (bounds[1] - bounds[0])


def _map_x(number, numbers, plot) -> float:
    """Map an iteration number into plot coordinates."""
    minimum, maximum = min(numbers), max(numbers)
    if minimum == maximum:
        return plot.center().x()
    return plot.left() + (number - minimum) / (maximum - minimum) * plot.width()


def _map_y(value, bounds, plot) -> float:
    """Map one axis value into inverted Qt plot coordinates."""
    fraction = (float(value) - bounds[0]) / (bounds[1] - bounds[0])
    return plot.bottom() - fraction * plot.height()


def _iteration_ticks(numbers) -> tuple[int, ...]:
    """Return compact first/middle/last iteration labels."""
    if len(numbers) <= 7:
        return tuple(numbers)
    return tuple(dict.fromkeys((numbers[0], numbers[len(numbers) // 2], numbers[-1])))
