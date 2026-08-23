"""Provides the shared geometry renderer for I- and H-shaped profiles."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QPainter, QPainterPath, QPolygonF

from .profile_preview_dimensions import dimension_symbol
from .profile_preview_drawing import (
    draw_horizontal_dimension,
    draw_internal_dimension,
    draw_profile_path,
    draw_vertical_dimension,
    fitted_profile_rect,
    positive_dimension,
)


def render_parallel_flange(painter: QPainter, area: QRectF, values: dict) -> None:
    """Render the common four-parameter parallel-flange section geometry."""
    height = positive_dimension(values, "height", 80.0)
    width = positive_dimension(values, "flange_width", 40.0)
    web_thickness = positive_dimension(values, "web_thickness", 4.0)
    flange_thickness = positive_dimension(values, "flange_thickness", 6.0)
    outer = fitted_profile_rect(area, width, height)
    x_scale = outer.width() / width
    y_scale = outer.height() / height
    web = min(web_thickness * x_scale, outer.width() * 0.8)
    flange = min(flange_thickness * y_scale, outer.height() * 0.4)
    x_left = outer.center().x() - web / 2.0
    x_right = outer.center().x() + web / 2.0
    y_top = outer.top() + flange
    y_bottom = outer.bottom() - flange
    points = (
        (outer.left(), outer.top()), (outer.right(), outer.top()),
        (outer.right(), y_top), (x_right, y_top),
        (x_right, y_bottom), (outer.right(), y_bottom),
        (outer.right(), outer.bottom()), (outer.left(), outer.bottom()),
        (outer.left(), y_bottom), (x_left, y_bottom),
        (x_left, y_top), (outer.left(), y_top),
    )
    path = QPainterPath()
    path.addPolygon(QPolygonF([QPointF(x, y) for x, y in points]))
    path.closeSubpath()
    draw_profile_path(painter, path)
    draw_horizontal_dimension(
        painter, outer.left(), outer.right(), outer.bottom() + 22.0,
        outer.bottom(), dimension_symbol("flange_width"),
    )
    draw_vertical_dimension(
        painter, outer.top(), outer.bottom(), outer.left() - 25.0,
        outer.left(), dimension_symbol("height"),
    )
    draw_internal_dimension(
        painter, QPointF(x_left, outer.center().y()),
        QPointF(x_right, outer.center().y()),
        dimension_symbol("web_thickness"), QPointF(0.0, -11.0),
    )
    draw_internal_dimension(
        painter, QPointF(outer.right() - 8.0, outer.top()),
        QPointF(outer.right() - 8.0, y_top),
        dimension_symbol("flange_thickness"), QPointF(14.0, 0.0),
    )
