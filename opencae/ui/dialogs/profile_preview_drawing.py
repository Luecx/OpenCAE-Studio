"""Provides shared vector primitives for technical profile previews."""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen

from opencae.ui.core.theme import PALETTE


def positive_dimension(values: dict, key: str, fallback: float = 1.0) -> float:
    """Read a finite positive drawing dimension without mutating model data."""
    try:
        value = float(values.get(key, fallback))
    except (TypeError, ValueError):
        return fallback
    return value if math.isfinite(value) and value > 0.0 else fallback


def fitted_profile_rect(area: QRectF, width: float, height: float) -> QRectF:
    """Fit a profile without changing the ratio of its physical dimensions."""
    drawing_area = area.adjusted(52.0, 20.0, -46.0, -42.0)
    ratio = width / max(height, 1e-12)
    if drawing_area.width() / max(drawing_area.height(), 1.0) > ratio:
        target_height = drawing_area.height()
        target_width = target_height * ratio
    else:
        target_width = drawing_area.width()
        target_height = target_width / ratio
    return QRectF(
        drawing_area.center().x() - target_width / 2.0,
        drawing_area.center().y() - target_height / 2.0,
        target_width,
        target_height,
    )


def draw_profile_path(painter: QPainter, path: QPainterPath) -> None:
    """Fill, hatch, and outline a closed section path using the app palette."""
    fill = QColor(PALETTE["accent_dim"])
    fill.setAlpha(185)
    hatch = QColor(PALETTE["accent"])
    hatch.setAlpha(48)

    painter.save()
    painter.fillPath(path, fill)
    painter.setClipPath(path)
    painter.setPen(QPen(hatch, 1.0))
    bounds = path.boundingRect().adjusted(-20.0, -20.0, 20.0, 20.0)
    diagonal = bounds.height() + 40.0
    x = bounds.left() - diagonal
    while x < bounds.right() + diagonal:
        painter.drawLine(
            QPointF(x, bounds.bottom()),
            QPointF(x + diagonal, bounds.top()),
        )
        x += 9.0
    painter.restore()

    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(PALETTE["text"]), 1.35))
    painter.drawPath(path)


def draw_horizontal_dimension(
    painter: QPainter,
    start_x: float,
    end_x: float,
    dimension_y: float,
    reference_y: float,
    label: str,
) -> None:
    """Draw one horizontal measure with extension lines and a centered label."""
    painter.save()
    _set_dimension_pen(painter)
    painter.drawLine(QPointF(start_x, reference_y), QPointF(start_x, dimension_y))
    painter.drawLine(QPointF(end_x, reference_y), QPointF(end_x, dimension_y))
    _draw_measure_line(
        painter,
        QPointF(start_x, dimension_y),
        QPointF(end_x, dimension_y),
        label,
        QPointF(0.0, 10.0 if dimension_y >= reference_y else -10.0),
    )
    painter.restore()


def draw_vertical_dimension(
    painter: QPainter,
    start_y: float,
    end_y: float,
    dimension_x: float,
    reference_x: float,
    label: str,
) -> None:
    """Draw one vertical measure with extension lines and a side label."""
    painter.save()
    _set_dimension_pen(painter)
    painter.drawLine(QPointF(reference_x, start_y), QPointF(dimension_x, start_y))
    painter.drawLine(QPointF(reference_x, end_y), QPointF(dimension_x, end_y))
    offset = QPointF(-15.0 if dimension_x <= reference_x else 15.0, 0.0)
    _draw_measure_line(
        painter,
        QPointF(dimension_x, start_y),
        QPointF(dimension_x, end_y),
        label,
        offset,
    )
    painter.restore()


def draw_thickness_dimension(
    painter: QPainter,
    start: QPointF,
    end: QPointF,
    label: str,
    *,
    label_at_end: bool = True,
) -> None:
    """Draw a thickness measure with its label beyond one geometry endpoint."""
    painter.save()
    _set_dimension_pen(painter)
    delta = end - start
    length = math.hypot(delta.x(), delta.y())
    if length > 1e-9:
        direction = QPointF(delta.x() / length, delta.y() / length)
        label_anchor = (
            end + direction * 20.0
            if label_at_end
            else start - direction * 20.0
        )
        midpoint = QPointF(
            (start.x() + end.x()) / 2.0,
            (start.y() + end.y()) / 2.0,
        )
        _draw_measure_line(painter, start, end, label, label_anchor - midpoint)
    painter.restore()


def draw_centerlines(painter: QPainter, rect: QRectF) -> None:
    """Draw muted horizontal and vertical centerlines through a profile."""
    painter.save()
    color = QColor(PALETTE["muted"])
    color.setAlpha(105)
    pen = QPen(color, 0.9, Qt.PenStyle.DashDotLine)
    painter.setPen(pen)
    painter.drawLine(
        QPointF(rect.left() - 8.0, rect.center().y()),
        QPointF(rect.right() + 8.0, rect.center().y()),
    )
    painter.drawLine(
        QPointF(rect.center().x(), rect.top() - 8.0),
        QPointF(rect.center().x(), rect.bottom() + 8.0),
    )
    painter.restore()


def draw_neutral_message(
    painter: QPainter,
    area: QRectF,
    title: str,
    detail: str = "",
) -> None:
    """Render a quiet fallback when no meaningful contour can be shown."""
    painter.save()
    painter.setPen(QColor(PALETTE["muted"]))
    font = QFont(painter.font())
    font.setPointSizeF(max(font.pointSizeF(), 9.0))
    painter.setFont(font)
    center = area.center()
    painter.drawLine(
        QPointF(center.x() - 30.0, center.y()),
        QPointF(center.x() + 30.0, center.y()),
    )
    painter.drawLine(
        QPointF(center.x(), center.y() - 24.0),
        QPointF(center.x(), center.y() + 24.0),
    )
    painter.drawEllipse(center, 3.0, 3.0)
    text_area = QRectF(area.left() + 12.0, center.y() + 34.0, area.width() - 24.0, 38.0)
    painter.drawText(
        text_area,
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
        title,
    )
    if detail:
        painter.drawText(
            text_area.adjusted(0.0, 18.0, 0.0, 18.0),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            detail,
        )
    painter.restore()


def _set_dimension_pen(painter: QPainter) -> None:
    """Apply the shared subdued annotation style to a painter."""
    painter.setPen(QPen(QColor(PALETTE["muted"]), 1.0))


def _draw_measure_line(
    painter: QPainter,
    start: QPointF,
    end: QPointF,
    label: str,
    text_offset: QPointF,
) -> None:
    """Draw a dimension segment, technical ticks, and unobscured text."""
    painter.drawLine(start, end)
    delta = end - start
    length = math.hypot(delta.x(), delta.y())
    if length <= 1e-9:
        return
    normal = QPointF(-delta.y() / length * 4.0, delta.x() / length * 4.0)
    tangent = QPointF(delta.x() / length * 2.0, delta.y() / length * 2.0)
    for point in (start, end):
        painter.drawLine(point - normal - tangent, point + normal + tangent)

    midpoint = QPointF((start.x() + end.x()) / 2.0, (start.y() + end.y()) / 2.0)
    text_center = midpoint + text_offset
    text_rect = QRectF(text_center.x() - 18.0, text_center.y() - 8.0, 36.0, 16.0)
    painter.fillRect(text_rect, QColor(PALETTE["panel_alt"]))
    painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, label)
