"""Draws the neutral preview for property-defined General profiles."""

from __future__ import annotations

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QPainter

from .profile_preview_dimensions import dimension_symbol
from .profile_preview_drawing import draw_neutral_message


def render_general(painter: QPainter, area: QRectF, values: dict) -> None:
    """Explain that General stores properties and has no geometric contour."""
    keys = ("area", "iyy", "izz", "iyz", "torsion_constant")
    symbols = "  ·  ".join(dimension_symbol(key) for key in keys if key in values)
    draw_neutral_message(
        painter,
        area.adjusted(0.0, -14.0, 0.0, -14.0),
        "No defined profile contour",
        symbols or "Section properties only",
    )
