"""Owns profile-type dispatch and the shared technical preview frame."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QColor, QPainter, QPen

from opencae.ui.core.theme import PALETTE

from .profile_preview_box import render_box
from .profile_preview_c import render_c_profile
from .profile_preview_circle import render_circle
from .profile_preview_general import render_general
from .profile_preview_graph import render_graph_profile
from .profile_preview_h import render_h_profile
from .profile_preview_i import render_i_profile
from .profile_preview_pipe import render_pipe
from .profile_preview_rectangle import render_rectangle
from .profile_preview_u import render_u_profile


ProfileRenderer = Callable[[QPainter, QRectF, dict], None]

_RENDERERS: dict[str, ProfileRenderer] = {
    "Rectangle": render_rectangle,
    "Box": render_box,
    "Pipe": render_pipe,
    "Circle": render_circle,
    "I-profile": render_i_profile,
    "H-profile": render_h_profile,
    "C-profile": render_c_profile,
    "Channel": render_c_profile,
    "U-profile": render_u_profile,
    "General": render_general,
    "Graph profile": render_graph_profile,
}


def render_profile_preview(
    painter: QPainter,
    bounds: QRectF,
    profile_type: str,
    dimensions: dict,
) -> None:
    """Paint the framed preview and dispatch only drawing data to its renderer."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    frame = bounds.adjusted(0.5, 0.5, -0.5, -0.5)
    painter.setPen(QPen(QColor(PALETTE["border_light"]), 1.0))
    painter.setBrush(QColor(PALETTE["panel_alt"]))
    painter.drawRoundedRect(frame, 5.0, 5.0)
    painter.setClipRect(frame.adjusted(1.0, 1.0, -1.0, -1.0))
    renderer = _RENDERERS.get(profile_type, render_general)
    renderer(painter, frame.adjusted(8.0, 8.0, -8.0, -8.0), dimensions)
    painter.restore()
