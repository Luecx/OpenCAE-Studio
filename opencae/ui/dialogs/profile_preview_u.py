"""Draws the technical preview for U-shaped channel profiles."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QPainter, QPainterPath, QPolygonF

from .profile_preview_dimensions import dimension_symbol
from .profile_preview_drawing import (
    draw_horizontal_dimension,
    draw_profile_path,
    draw_thickness_dimension,
    draw_vertical_dimension,
    fitted_profile_rect,
    positive_dimension,
)


def render_u_profile(painter: QPainter, area: QRectF, values: dict) -> None:
    """Render the rotated channel interpretation used by U-profile calculations."""
    overall_width = positive_dimension(values, "height", 80.0)
    leg_height = positive_dimension(values, "flange_width", 40.0)
    base_thickness = positive_dimension(values, "web_thickness", 4.0)
    leg_thickness = positive_dimension(values, "flange_thickness", 6.0)
    outer = fitted_profile_rect(area, overall_width, leg_height)
    base = min(base_thickness * outer.height() / leg_height, outer.height())
    leg = min(leg_thickness * outer.width() / overall_width, outer.width() * 0.5)
    x_left = outer.left() + leg
    x_right = outer.right() - leg
    y_base = outer.bottom() - base
    points = (
        (outer.left(), outer.top()), (x_left, outer.top()),
        (x_left, y_base), (x_right, y_base),
        (x_right, outer.top()), (outer.right(), outer.top()),
        (outer.right(), outer.bottom()), (outer.left(), outer.bottom()),
    )
    path = QPainterPath()
    path.addPolygon(QPolygonF([QPointF(x, y) for x, y in points]))
    path.closeSubpath()
    draw_profile_path(painter, path)
    draw_horizontal_dimension(
        painter, outer.left(), outer.right(), outer.bottom() + 22.0,
        outer.bottom(), dimension_symbol("height"),
    )
    draw_vertical_dimension(
        painter, outer.top(), outer.bottom(), outer.left() - 25.0,
        outer.left(), dimension_symbol("flange_width"),
    )
    draw_thickness_dimension(
        painter, QPointF(outer.center().x(), y_base),
        QPointF(outer.center().x(), outer.bottom()),
        dimension_symbol("web_thickness"), label_at_end=False,
    )
    draw_thickness_dimension(
        painter, QPointF(outer.left(), outer.top() + 12.0),
        QPointF(x_left, outer.top() + 12.0),
        dimension_symbol("flange_thickness"),
    )
