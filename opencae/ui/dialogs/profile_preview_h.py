"""Dispatches H-profile previews to the shared parallel-flange renderer."""

from __future__ import annotations

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QPainter

from .profile_preview_parallel_flange import render_parallel_flange


def render_h_profile(painter: QPainter, area: QRectF, values: dict) -> None:
    """Render an H-profile using the model's parallel-flange dimensions."""
    render_parallel_flange(painter, area, values)
