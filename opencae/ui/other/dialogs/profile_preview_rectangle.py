"""Draws the technical preview for solid rectangular profiles."""

from __future__ import annotations

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QPainter, QPainterPath

from .profile_preview_dimensions import dimension_symbol
from .profile_preview_drawing import (
    draw_horizontal_dimension,
    draw_profile_path,
    draw_vertical_dimension,
    fitted_profile_rect,
    positive_dimension,
)


def render_rectangle(painter: QPainter, area: QRectF, values: dict) -> None:
    """Render a filled rectangle annotated with its model width and height."""
    width = positive_dimension(values, "width", 40.0)
    height = positive_dimension(values, "height", 20.0)
    profile = fitted_profile_rect(area, width, height)
    path = QPainterPath()
    path.addRect(profile)
    draw_profile_path(painter, path)
    draw_horizontal_dimension(
        painter, profile.left(), profile.right(), profile.bottom() + 22.0,
        profile.bottom(), dimension_symbol("width"),
    )
    draw_vertical_dimension(
        painter, profile.top(), profile.bottom(), profile.left() - 25.0,
        profile.left(), dimension_symbol("height"),
    )
