"""Draws the technical preview for hollow rectangular box profiles."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QPainter, QPainterPath

from .profile_preview_dimensions import dimension_symbol
from .profile_preview_drawing import (
    draw_horizontal_dimension,
    draw_profile_path,
    draw_thickness_dimension,
    draw_vertical_dimension,
    fitted_profile_rect,
    positive_dimension,
)


def render_box(painter: QPainter, area: QRectF, values: dict) -> None:
    """Render a hollow box using width, height, and wall thickness keys."""
    width = positive_dimension(values, "width", 40.0)
    height = positive_dimension(values, "height", 20.0)
    thickness = positive_dimension(values, "thickness", 2.0)
    outer = fitted_profile_rect(area, width, height)
    scale = min(outer.width() / width, outer.height() / height)
    wall = min(thickness * scale, min(outer.width(), outer.height()) * 0.5)
    inner = outer.adjusted(wall, wall, -wall, -wall)
    path = QPainterPath()
    path.setFillRule(Qt.FillRule.OddEvenFill)
    path.addRect(outer)
    if inner.width() > 0.5 and inner.height() > 0.5:
        path.addRect(inner)
    draw_profile_path(painter, path)
    draw_horizontal_dimension(
        painter, outer.left(), outer.right(), outer.bottom() + 22.0,
        outer.bottom(), dimension_symbol("width"),
    )
    draw_vertical_dimension(
        painter, outer.top(), outer.bottom(), outer.left() - 25.0,
        outer.left(), dimension_symbol("height"),
    )
    if inner.width() > 0.5:
        y = outer.top() + wall / 2.0
        draw_thickness_dimension(
            painter, QPointF(outer.left(), y), QPointF(inner.left(), y),
            dimension_symbol("thickness"), label_at_end=False,
        )
