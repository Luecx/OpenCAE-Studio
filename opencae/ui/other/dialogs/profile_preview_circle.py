"""Draws the technical preview for solid circular profiles."""

from __future__ import annotations

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QPainter, QPainterPath

from .profile_preview_dimensions import dimension_symbol
from .profile_preview_drawing import (
    draw_centerlines,
    draw_horizontal_dimension,
    draw_profile_path,
    fitted_profile_rect,
    positive_dimension,
)


def render_circle(painter: QPainter, area: QRectF, values: dict) -> None:
    """Render a solid circle and annotate its existing diameter parameter."""
    diameter = positive_dimension(values, "diameter", 30.0)
    profile = fitted_profile_rect(area, diameter, diameter)
    path = QPainterPath()
    path.addEllipse(profile)
    draw_profile_path(painter, path)
    draw_centerlines(painter, profile)
    draw_horizontal_dimension(
        painter, profile.left(), profile.right(), profile.bottom() + 22.0,
        profile.bottom(), dimension_symbol("diameter"),
    )
