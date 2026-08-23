"""Draws graph-profile previews from the editor's real nodes and segments."""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen

from opencae.ui.core.theme import PALETTE

from .profile_preview_drawing import draw_neutral_message


def render_graph_profile(painter: QPainter, area: QRectF, values: dict) -> None:
    """Fit and render valid graph segments while tolerating partial editor rows."""
    nodes = _parse_nodes(values.get("nodes", ""))
    segments = _parse_segments(values.get("segments", ""), nodes)
    if not segments:
        draw_neutral_message(painter, area, "No valid graph geometry")
        return

    # Thickness participates in fitting, so large walls cannot be clipped and
    # every segment uses the same coordinate-to-pixel scale for length and width.
    min_y = min(
        min(first[0], second[0]) - thickness / 2.0
        for first, second, thickness in segments
    )
    max_y = max(
        max(first[0], second[0]) + thickness / 2.0
        for first, second, thickness in segments
    )
    min_z = min(
        min(first[1], second[1]) - thickness / 2.0
        for first, second, thickness in segments
    )
    max_z = max(
        max(first[1], second[1]) + thickness / 2.0
        for first, second, thickness in segments
    )
    span_y = max_y - min_y
    span_z = max_z - min_z

    target = area.adjusted(30.0, 22.0, -30.0, -30.0)
    scale = min(target.width() / span_y, target.height() / span_z)
    origin_x = target.center().x() - (min_y + max_y) * scale / 2.0
    origin_y = target.center().y() + (min_z + max_z) * scale / 2.0

    def mapped(point: tuple[float, float]) -> QPointF:
        """Map graph y/z coordinates into the fitted preview rectangle."""
        return QPointF(origin_x + point[0] * scale, origin_y - point[1] * scale)

    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    for first, second, thickness in segments:
        stroke = thickness * scale
        outline = QPen(QColor(PALETTE["text"]), stroke + 1.5)
        outline.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(outline)
        painter.drawLine(mapped(first), mapped(second))
        fill = QColor(PALETTE["accent_dim"])
        fill.setAlpha(230)
        section_pen = QPen(fill, stroke)
        section_pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(section_pen)
        painter.drawLine(mapped(first), mapped(second))

        if stroke >= 4.0:
            hatch = QColor(PALETTE["accent"])
            hatch.setAlpha(115)
            painter.setPen(QPen(hatch, 0.8, Qt.PenStyle.DashLine))
            painter.drawLine(mapped(first), mapped(second))
    _draw_axes(painter, area)
    painter.restore()


def _parse_nodes(text) -> dict[int, tuple[float, float]]:
    """Parse complete finite graph node rows and ignore unfinished input."""
    nodes = {}
    for line in str(text or "").replace(";", "\n").splitlines():
        try:
            tag, y, z = (item.strip() for item in line.split(",", 2))
            point = (float(y), float(z))
            if math.isfinite(point[0]) and math.isfinite(point[1]):
                nodes[int(tag)] = point
        except (TypeError, ValueError):
            continue
    return nodes


def _parse_segments(
    text,
    nodes: dict[int, tuple[float, float]],
) -> list[tuple[tuple[float, float], tuple[float, float], float]]:
    """Resolve complete positive-thickness graph segments against valid nodes."""
    segments = []
    for line in str(text or "").replace(";", "\n").splitlines():
        try:
            first, second, thickness_text = (
                item.strip() for item in line.split(",", 2)
            )
            thickness = float(thickness_text)
            start = nodes[int(first)]
            end = nodes[int(second)]
            if thickness > 0.0 and math.isfinite(thickness) and start != end:
                segments.append((start, end, thickness))
        except (TypeError, ValueError, KeyError):
            continue
    return segments


def _draw_axes(painter: QPainter, area: QRectF) -> None:
    """Draw a small y/z orientation mark without implying graph dimensions."""
    origin = QPointF(area.right() - 30.0, area.bottom() - 24.0)
    painter.setPen(QPen(QColor(PALETTE["muted"]), 0.9))
    painter.drawLine(origin, origin + QPointF(17.0, 0.0))
    painter.drawLine(origin, origin + QPointF(0.0, -17.0))
    painter.drawText(QRectF(origin.x() + 18.0, origin.y() - 8.0, 12.0, 16.0), "y")
    painter.drawText(QRectF(origin.x() - 6.0, origin.y() - 31.0, 12.0, 14.0), "z")
