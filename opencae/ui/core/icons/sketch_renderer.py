"""Small vector icons used by the parametric Sketcher ribbon."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

from opencae.ui.core.theme import PALETTE

from .kinds import IconKind


_SKETCH_KINDS = {
    kind
    for kind in IconKind
    if kind.name.startswith("SKETCH_")
}


def _point(painter: QPainter, size: int, x: float, y: float, color: QColor) -> None:
    radius = max(1.7, size * 0.055)
    painter.setBrush(color)
    painter.drawEllipse(
        QRectF(size * x - radius, size * y - radius, 2.0 * radius, 2.0 * radius)
    )
    painter.setBrush(Qt.BrushStyle.NoBrush)


def _line(painter: QPainter, size: int, a, b) -> None:
    painter.drawLine(
        QPointF(size * a[0], size * a[1]),
        QPointF(size * b[0], size * b[1]),
    )


def _arrow(painter: QPainter, size: int, a, b) -> None:
    _line(painter, size, a, b)
    direction = 1.0 if b[0] >= a[0] else -1.0
    _line(painter, size, b, (b[0] - 0.10 * direction, b[1] - 0.07))
    _line(painter, size, b, (b[0] - 0.10 * direction, b[1] + 0.07))


def make_sketch_icon(
    kind: IconKind,
    size: int = 40,
    accent: str | None = None,
) -> QIcon | None:
    if kind not in _SKETCH_KINDS:
        return None

    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    foreground = QColor(accent or PALETTE["accent"])
    muted = QColor(PALETTE.get("muted", "#98a2ad"))
    pen = QPen(
        foreground,
        max(1.6, size / 20.0),
        Qt.PenStyle.SolidLine,
        Qt.PenCapStyle.RoundCap,
        Qt.PenJoinStyle.RoundJoin,
    )
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if kind == IconKind.SKETCH_SELECT:
        path = QPainterPath(QPointF(size * 0.25, size * 0.15))
        path.lineTo(size * 0.25, size * 0.76)
        path.lineTo(size * 0.42, size * 0.61)
        path.lineTo(size * 0.53, size * 0.84)
        path.lineTo(size * 0.65, size * 0.78)
        path.lineTo(size * 0.54, size * 0.56)
        path.lineTo(size * 0.78, size * 0.55)
        path.closeSubpath()
        painter.drawPath(path)

    elif kind == IconKind.SKETCH_POINT:
        _point(painter, size, 0.50, 0.50, foreground)
        painter.setPen(QPen(muted, max(1.0, size / 32.0)))
        _line(painter, size, (0.25, 0.50), (0.75, 0.50))
        _line(painter, size, (0.50, 0.25), (0.50, 0.75))

    elif kind == IconKind.SKETCH_LINE:
        _line(painter, size, (0.20, 0.72), (0.80, 0.28))
        _point(painter, size, 0.20, 0.72, foreground)
        _point(painter, size, 0.80, 0.28, foreground)

    elif kind == IconKind.SKETCH_POLYLINE:
        points = ((0.15, 0.68), (0.37, 0.30), (0.60, 0.65), (0.84, 0.28))
        for first, second in zip(points, points[1:]):
            _line(painter, size, first, second)
        for x, y in points:
            _point(painter, size, x, y, foreground)

    elif kind == IconKind.SKETCH_RECTANGLE:
        painter.drawRect(QRectF(size * 0.18, size * 0.25, size * 0.64, size * 0.50))
        for x, y in ((0.18, 0.25), (0.82, 0.25), (0.82, 0.75), (0.18, 0.75)):
            _point(painter, size, x, y, foreground)

    elif kind == IconKind.SKETCH_CIRCLE:
        painter.drawEllipse(QRectF(size * 0.20, size * 0.20, size * 0.60, size * 0.60))
        _point(painter, size, 0.50, 0.50, muted)

    elif kind in {IconKind.SKETCH_ARC, IconKind.SKETCH_ARC_CENTER}:
        painter.drawArc(
            QRectF(size * 0.18, size * 0.18, size * 0.64, size * 0.64),
            20 * 16,
            220 * 16,
        )
        _point(painter, size, 0.50, 0.50, muted)
        _line(painter, size, (0.50, 0.50), (0.77, 0.32))

    elif kind == IconKind.SKETCH_ARC_3POINT:
        painter.drawArc(
            QRectF(size * 0.17, size * 0.22, size * 0.66, size * 0.56),
            20 * 16,
            220 * 16,
        )
        for x, y in ((0.22, 0.63), (0.50, 0.25), (0.78, 0.63)):
            _point(painter, size, x, y, foreground if y < 0.4 else muted)

    elif kind == IconKind.SKETCH_ELLIPSE:
        painter.save()
        painter.translate(size * 0.50, size * 0.50)
        painter.rotate(-25.0)
        painter.drawEllipse(QRectF(-size * 0.34, -size * 0.20, size * 0.68, size * 0.40))
        painter.restore()
        _point(painter, size, 0.50, 0.50, muted)

    elif kind == IconKind.SKETCH_SPLINE:
        path = QPainterPath(QPointF(size * 0.12, size * 0.68))
        path.cubicTo(
            QPointF(size * 0.30, size * 0.08),
            QPointF(size * 0.55, size * 0.90),
            QPointF(size * 0.86, size * 0.30),
        )
        painter.drawPath(path)
        for x, y in ((0.12, 0.68), (0.40, 0.37), (0.63, 0.59), (0.86, 0.30)):
            _point(painter, size, x, y, muted)

    elif kind == IconKind.SKETCH_SLOT:
        path = QPainterPath()
        path.moveTo(size * 0.28, size * 0.25)
        path.lineTo(size * 0.72, size * 0.25)
        path.arcTo(QRectF(size * 0.57, size * 0.25, size * 0.30, size * 0.50), 90, -180)
        path.lineTo(size * 0.28, size * 0.75)
        path.arcTo(QRectF(size * 0.13, size * 0.25, size * 0.30, size * 0.50), 270, -180)
        painter.drawPath(path)

    elif kind == IconKind.SKETCH_PRIMITIVES_MORE:
        painter.drawRect(QRectF(size * 0.14, size * 0.18, size * 0.28, size * 0.24))
        painter.drawEllipse(QRectF(size * 0.56, size * 0.18, size * 0.27, size * 0.27))
        painter.drawArc(QRectF(size * 0.24, size * 0.52, size * 0.50, size * 0.30), 0, 180 * 16)

    elif kind == IconKind.SKETCH_CONSTRUCTION:
        dashed = QPen(foreground, max(1.5, size / 22.0), Qt.PenStyle.DashLine)
        dashed.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(dashed)
        _line(painter, size, (0.14, 0.70), (0.86, 0.30))
        painter.setPen(QPen(muted, max(1.0, size / 34.0)))
        _line(painter, size, (0.50, 0.15), (0.50, 0.85))

    elif kind == IconKind.SKETCH_GRID:
        for value in (0.28, 0.50, 0.72):
            _line(painter, size, (0.16, value), (0.84, value))
            _line(painter, size, (value, 0.16), (value, 0.84))

    elif kind == IconKind.SKETCH_SNAP:
        painter.drawEllipse(QRectF(size * 0.18, size * 0.18, size * 0.48, size * 0.48))
        _point(painter, size, 0.42, 0.42, foreground)
        _line(painter, size, (0.55, 0.55), (0.82, 0.82))
        _point(painter, size, 0.82, 0.82, muted)

    elif kind in {IconKind.SKETCH_CONSTRAINT, IconKind.SKETCH_CONSTRAINT_MORE}:
        _line(painter, size, (0.20, 0.70), (0.72, 0.70))
        _line(painter, size, (0.72, 0.70), (0.72, 0.22))
        painter.drawRect(QRectF(size * 0.58, size * 0.56, size * 0.14, size * 0.14))
        if kind == IconKind.SKETCH_CONSTRAINT_MORE:
            for x in (0.30, 0.50, 0.70):
                _point(painter, size, x, 0.88, muted)

    elif kind == IconKind.SKETCH_CONSTRAINT_COINCIDENT:
        _line(painter, size, (0.18, 0.68), (0.82, 0.32))
        _point(painter, size, 0.50, 0.50, foreground)
        painter.drawEllipse(QRectF(size * 0.42, size * 0.42, size * 0.16, size * 0.16))

    elif kind == IconKind.SKETCH_CONSTRAINT_HORIZONTAL:
        _line(painter, size, (0.18, 0.50), (0.82, 0.50))
        _point(painter, size, 0.18, 0.50, muted)
        _point(painter, size, 0.82, 0.50, muted)

    elif kind == IconKind.SKETCH_CONSTRAINT_VERTICAL:
        _line(painter, size, (0.50, 0.16), (0.50, 0.84))
        _point(painter, size, 0.50, 0.16, muted)
        _point(painter, size, 0.50, 0.84, muted)

    elif kind == IconKind.SKETCH_CONSTRAINT_PARALLEL:
        _line(painter, size, (0.20, 0.66), (0.68, 0.26))
        _line(painter, size, (0.34, 0.80), (0.82, 0.40))

    elif kind == IconKind.SKETCH_CONSTRAINT_PERPENDICULAR:
        _line(painter, size, (0.22, 0.68), (0.76, 0.68))
        _line(painter, size, (0.54, 0.68), (0.54, 0.20))
        painter.drawRect(QRectF(size * 0.44, size * 0.58, size * 0.10, size * 0.10))

    elif kind == IconKind.SKETCH_CONSTRAINT_TANGENT:
        painter.drawEllipse(QRectF(size * 0.20, size * 0.28, size * 0.42, size * 0.42))
        _line(painter, size, (0.28, 0.78), (0.82, 0.24))
        _point(painter, size, 0.52, 0.54, foreground)

    elif kind == IconKind.SKETCH_CONSTRAINT_EQUAL:
        _line(painter, size, (0.20, 0.38), (0.80, 0.38))
        _line(painter, size, (0.20, 0.62), (0.80, 0.62))

    elif kind == IconKind.SKETCH_CONSTRAINT_CONCENTRIC:
        painter.drawEllipse(QRectF(size * 0.16, size * 0.16, size * 0.68, size * 0.68))
        painter.drawEllipse(QRectF(size * 0.31, size * 0.31, size * 0.38, size * 0.38))
        _point(painter, size, 0.50, 0.50, muted)

    elif kind == IconKind.SKETCH_CONSTRAINT_MIDPOINT:
        _line(painter, size, (0.16, 0.62), (0.84, 0.38))
        _point(painter, size, 0.50, 0.50, foreground)
        _line(painter, size, (0.44, 0.30), (0.56, 0.70))

    elif kind == IconKind.SKETCH_CONSTRAINT_COLLINEAR:
        _line(painter, size, (0.14, 0.72), (0.86, 0.28))
        for x, y in ((0.26, 0.65), (0.50, 0.50), (0.74, 0.35)):
            _point(painter, size, x, y, muted)

    elif kind == IconKind.SKETCH_CONSTRAINT_POINT_ON:
        painter.drawEllipse(QRectF(size * 0.18, size * 0.18, size * 0.64, size * 0.64))
        _point(painter, size, 0.50, 0.18, foreground)

    elif kind == IconKind.SKETCH_CONSTRAINT_SYMMETRY:
        dashed = QPen(muted, max(1.2, size / 28.0), Qt.PenStyle.DashLine)
        painter.setPen(dashed)
        _line(painter, size, (0.50, 0.12), (0.50, 0.88))
        painter.setPen(pen)
        _line(painter, size, (0.18, 0.66), (0.38, 0.34))
        _line(painter, size, (0.82, 0.66), (0.62, 0.34))

    elif kind == IconKind.SKETCH_CONSTRAINT_FIXED:
        painter.drawRect(QRectF(size * 0.26, size * 0.44, size * 0.48, size * 0.36))
        painter.drawArc(QRectF(size * 0.34, size * 0.18, size * 0.32, size * 0.42), 0, 180 * 16)

    elif kind == IconKind.SKETCH_DIMENSION:
        _line(painter, size, (0.20, 0.34), (0.20, 0.72))
        _line(painter, size, (0.80, 0.34), (0.80, 0.72))
        _arrow(painter, size, (0.50, 0.48), (0.24, 0.48))
        _arrow(painter, size, (0.50, 0.48), (0.76, 0.48))

    elif kind == IconKind.SKETCH_DIMENSION_DISTANCE:
        _line(painter, size, (0.18, 0.66), (0.18, 0.30))
        _line(painter, size, (0.82, 0.66), (0.82, 0.30))
        _arrow(painter, size, (0.50, 0.48), (0.22, 0.48))
        _arrow(painter, size, (0.50, 0.48), (0.78, 0.48))

    elif kind == IconKind.SKETCH_DIMENSION_HORIZONTAL:
        _arrow(painter, size, (0.50, 0.50), (0.18, 0.50))
        _arrow(painter, size, (0.50, 0.50), (0.82, 0.50))
        _line(painter, size, (0.18, 0.30), (0.18, 0.70))
        _line(painter, size, (0.82, 0.30), (0.82, 0.70))

    elif kind == IconKind.SKETCH_DIMENSION_VERTICAL:
        _line(painter, size, (0.30, 0.18), (0.70, 0.18))
        _line(painter, size, (0.30, 0.82), (0.70, 0.82))
        _line(painter, size, (0.50, 0.50), (0.50, 0.18))
        _line(painter, size, (0.50, 0.50), (0.50, 0.82))
        _line(painter, size, (0.50, 0.18), (0.44, 0.28))
        _line(painter, size, (0.50, 0.18), (0.56, 0.28))
        _line(painter, size, (0.50, 0.82), (0.44, 0.72))
        _line(painter, size, (0.50, 0.82), (0.56, 0.72))

    elif kind == IconKind.SKETCH_DIMENSION_ANGLE:
        _line(painter, size, (0.26, 0.72), (0.50, 0.50))
        _line(painter, size, (0.50, 0.50), (0.80, 0.30))
        painter.drawArc(QRectF(size * 0.34, size * 0.34, size * 0.34, size * 0.34), 25 * 16, 105 * 16)

    elif kind == IconKind.SKETCH_DIMENSION_RADIUS:
        painter.drawEllipse(QRectF(size * 0.18, size * 0.18, size * 0.64, size * 0.64))
        _arrow(painter, size, (0.50, 0.50), (0.78, 0.32))
        _point(painter, size, 0.50, 0.50, muted)

    elif kind == IconKind.SKETCH_DIMENSION_DIAMETER:
        painter.drawEllipse(QRectF(size * 0.18, size * 0.18, size * 0.64, size * 0.64))
        _line(painter, size, (0.22, 0.72), (0.78, 0.28))
        _line(painter, size, (0.22, 0.72), (0.30, 0.59))
        _line(painter, size, (0.78, 0.28), (0.70, 0.41))

    painter.end()
    return QIcon(pixmap)


__all__ = ["make_sketch_icon"]
