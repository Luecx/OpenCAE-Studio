"""Draws the technical preview for hollow circular pipe profiles."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QPainter, QPainterPath

from .profile_preview_dimensions import dimension_symbol
from .profile_preview_drawing import (
    draw_centerlines,
    draw_horizontal_dimension,
    draw_profile_path,
    draw_thickness_dimension,
    fitted_profile_rect,
    positive_dimension,
)


def render_pipe(painter: QPainter, area: QRectF, values: dict) -> None:
    """Render concentric pipe contours from diameter and wall thickness."""
    diameter = positive_dimension(values, "diameter", 30.0)
    thickness = positive_dimension(values, "thickness", 2.0)
    outer = fitted_profile_rect(area, diameter, diameter)
    scale = outer.width() / diameter
    wall = min(thickness * scale, outer.width() * 0.5)
    inner = outer.adjusted(wall, wall, -wall, -wall)
    path = QPainterPath()
    path.setFillRule(Qt.FillRule.OddEvenFill)
    path.addEllipse(outer)
    if inner.width() > 0.5:
        path.addEllipse(inner)
    draw_profile_path(painter, path)
    draw_centerlines(painter, outer)
    draw_horizontal_dimension(
        painter, outer.left(), outer.right(), outer.bottom() + 22.0,
        outer.bottom(), dimension_symbol("diameter"),
    )
    if inner.width() > 0.5:
        y = outer.center().y()
        draw_thickness_dimension(
            painter, QPointF(inner.right(), y), QPointF(outer.right(), y),
            dimension_symbol("thickness"),
        )
