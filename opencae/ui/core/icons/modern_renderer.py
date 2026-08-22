from __future__ import annotations

from math import hypot

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

from opencae.ui.core.theme import PALETTE

from .kinds import IconKind
from .legacy_shapes import draw_cube


_CUSTOM_KINDS = {
    IconKind.NEW_PROJECT,
    IconKind.OPEN_PROJECT,
    IconKind.FIT_VIEW,
    IconKind.UNDO,
    IconKind.REDO,
    IconKind.REBUILD,
    IconKind.SUPPRESS,
    IconKind.MESH_IMPORT,
    IconKind.EDGE_SEED,
    IconKind.DATUM_POINT,
    IconKind.DATUM_VECTOR,
    IconKind.DATUM_PLANE,
    IconKind.PREVIEW_DECK,
    IconKind.WRITE_DECK,
    IconKind.NEW_ANALYSIS,
    IconKind.TOPOLOGY,
    IconKind.FILTER,
    IconKind.THRESHOLD,
    IconKind.JOB_MONITOR,
    IconKind.DUPLICATE,
    IconKind.CONSTRAINT_EQUATION,
    IconKind.VISIBILITY,
    IconKind.UNDEFORMED,
    IconKind.QUERY_NODE,
    IconKind.QUERY_ELEMENT,
    IconKind.RANGE,
}


def _arrow(painter, start, end, size, color, width=None):
    width = width or max(1.7, size / 20)
    painter.setPen(
        QPen(
            color,
            width,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
    )
    painter.drawLine(start, end)
    dx = end.x() - start.x()
    dy = end.y() - start.y()
    length = hypot(dx, dy)
    if length <= 0:
        return
    ux, uy = dx / length, dy / length
    head = size * .14
    wing = head * .55
    left = QPointF(
        end.x() - ux * head + uy * wing,
        end.y() - uy * head - ux * wing,
    )
    right = QPointF(
        end.x() - ux * head - uy * wing,
        end.y() - uy * head + ux * wing,
    )
    painter.drawLine(end, left)
    painter.drawLine(end, right)


def _document(painter, size, color):
    path = QPainterPath()
    path.moveTo(size * .22, size * .12)
    path.lineTo(size * .62, size * .12)
    path.lineTo(size * .80, size * .30)
    path.lineTo(size * .80, size * .86)
    path.lineTo(size * .22, size * .86)
    path.closeSubpath()
    painter.drawPath(path)
    painter.drawLine(
        QPointF(size * .62, size * .12),
        QPointF(size * .62, size * .30),
    )
    painter.drawLine(
        QPointF(size * .62, size * .30),
        QPointF(size * .80, size * .30),
    )


def _node(painter, x, y, size, color, radius=None, filled=True):
    radius = radius or size * .065
    rect = QRectF(size * x - radius, size * y - radius, radius * 2, radius * 2)
    painter.setBrush(color if filled else Qt.BrushStyle.NoBrush)
    painter.drawEllipse(rect)
    painter.setBrush(Qt.BrushStyle.NoBrush)


def make_modern_icon(
    kind: IconKind,
    size: int = 40,
    accent: str | None = None,
) -> QIcon | None:
    if kind not in _CUSTOM_KINDS:
        return None

    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    fg = QColor(accent or PALETTE["accent"])
    muted = QColor("#aab4bf")
    soft = QColor(fg.red(), fg.green(), fg.blue(), 62)
    pen = QPen(
        fg,
        max(1.6, size / 20),
        Qt.PenStyle.SolidLine,
        Qt.PenCapStyle.RoundCap,
        Qt.PenJoinStyle.RoundJoin,
    )
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if kind == IconKind.NEW_PROJECT:
        _document(painter, size, muted)
        painter.setPen(pen)
        painter.drawLine(
            QPointF(size * .64, size * .68),
            QPointF(size * .90, size * .68),
        )
        painter.drawLine(
            QPointF(size * .77, size * .55),
            QPointF(size * .77, size * .81),
        )

    elif kind == IconKind.OPEN_PROJECT:
        folder = QPainterPath()
        folder.moveTo(size * .12, size * .30)
        folder.lineTo(size * .39, size * .30)
        folder.lineTo(size * .48, size * .40)
        folder.lineTo(size * .87, size * .40)
        folder.lineTo(size * .78, size * .78)
        folder.lineTo(size * .12, size * .78)
        folder.closeSubpath()
        painter.setBrush(QColor(fg.red(), fg.green(), fg.blue(), 35))
        painter.drawPath(folder)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        _arrow(
            painter,
            QPointF(size * .46, size * .20),
            QPointF(size * .72, size * .20),
            size,
            fg,
        )

    elif kind == IconKind.FIT_VIEW:
        draw_cube(painter, QRectF(size * .20, size * .20, size * .60, size * .60), muted)
        painter.setPen(pen)
        for x1, y1, x2, y2, x3, y3 in (
            (.10, .30, .10, .10, .30, .10),
            (.70, .10, .90, .10, .90, .30),
            (.10, .70, .10, .90, .30, .90),
            (.70, .90, .90, .90, .90, .70),
        ):
            painter.drawLine(QPointF(size * x1, size * y1), QPointF(size * x2, size * y2))
            painter.drawLine(QPointF(size * x2, size * y2), QPointF(size * x3, size * y3))

    elif kind in {IconKind.UNDO, IconKind.REDO}:
        undo = kind == IconKind.UNDO
        rect = QRectF(size * .18, size * .20, size * .64, size * .58)
        start = 35 * 16 if undo else 145 * 16
        span = 230 * 16 if undo else -230 * 16
        painter.drawArc(rect, start, span)
        if undo:
            tip = QPointF(size * .18, size * .40)
            painter.drawLine(tip, QPointF(size * .34, size * .30))
            painter.drawLine(tip, QPointF(size * .32, size * .48))
        else:
            tip = QPointF(size * .82, size * .40)
            painter.drawLine(tip, QPointF(size * .66, size * .30))
            painter.drawLine(tip, QPointF(size * .68, size * .48))

    elif kind == IconKind.DUPLICATE:
        draw_cube(
            painter,
            QRectF(size * .08, size * .10, size * .62, size * .62),
            muted,
        )
        draw_cube(
            painter,
            QRectF(size * .27, size * .28, size * .62, size * .62),
            fg,
        )

    elif kind == IconKind.REBUILD:
        draw_cube(
            painter,
            QRectF(size * .15, size * .20, size * .58, size * .58),
            muted,
        )
        painter.setPen(pen)
        painter.drawArc(
            QRectF(size * .28, size * .10, size * .60, size * .60),
            -40 * 16,
            235 * 16,
        )
        tip = QPointF(size * .80, size * .19)
        painter.drawLine(tip, QPointF(size * .68, size * .15))
        painter.drawLine(tip, QPointF(size * .75, size * .31))

    elif kind == IconKind.SUPPRESS:
        draw_cube(
            painter,
            QRectF(size * .16, size * .16, size * .66, size * .66),
            muted,
        )
        painter.setPen(QPen(fg, max(2.4, size / 14)))
        painter.drawLine(
            QPointF(size * .18, size * .82),
            QPointF(size * .82, size * .18),
        )

    elif kind == IconKind.MESH_IMPORT:
        painter.setPen(QPen(muted, max(1.2, size / 28)))
        for index in range(4):
            y = size * (.38 + index * .13)
            painter.drawLine(QPointF(size * .20, y), QPointF(size * .82, y))
            x = size * (.20 + index * .20)
            painter.drawLine(QPointF(x, size * .38), QPointF(x, size * .77))
        _arrow(
            painter,
            QPointF(size * .50, size * .08),
            QPointF(size * .50, size * .33),
            size,
            fg,
        )

    elif kind == IconKind.EDGE_SEED:
        draw_cube(
            painter,
            QRectF(size * .13, size * .14, size * .72, size * .68),
            muted,
        )
        painter.setPen(QPen(fg, max(2.2, size / 16)))
        painter.drawLine(
            QPointF(size * .29, size * .63),
            QPointF(size * .55, size * .77),
        )
        for t in (.36, .45, .54):
            x = size * t
            y = size * (.63 + (t - .29) * .54)
            painter.drawLine(
                QPointF(x - size * .025, y + size * .045),
                QPointF(x + size * .025, y - size * .045),
            )

    elif kind == IconKind.DATUM_POINT:
        painter.setPen(QPen(muted, max(1.2, size / 30)))
        tick = size * .16
        inset = size * .18
        for x, y, sx, sy in (
            (inset, inset, 1, 1),
            (size - inset, inset, -1, 1),
            (inset, size - inset, 1, -1),
            (size - inset, size - inset, -1, -1),
        ):
            painter.drawLine(QPointF(x, y), QPointF(x + sx * tick, y))
            painter.drawLine(QPointF(x, y), QPointF(x, y + sy * tick))
        _node(painter, .50, .50, size, fg, radius=size * .09, filled=True)

    elif kind == IconKind.DATUM_VECTOR:
        _node(painter, .22, .72, size, muted, radius=size * .055, filled=True)
        _arrow(
            painter,
            QPointF(size * .25, size * .69),
            QPointF(size * .78, size * .22),
            size,
            fg,
            max(2.0, size / 17),
        )

    elif kind == IconKind.DATUM_PLANE:
        plane = QPainterPath()
        plane.moveTo(size * .12, size * .63)
        plane.lineTo(size * .38, size * .29)
        plane.lineTo(size * .86, size * .40)
        plane.lineTo(size * .60, size * .74)
        plane.closeSubpath()
        painter.setBrush(soft)
        painter.drawPath(plane)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        _arrow(
            painter,
            QPointF(size * .50, size * .52),
            QPointF(size * .66, size * .13),
            size,
            fg,
        )

    elif kind == IconKind.CONSTRAINT_EQUATION:
        painter.setPen(pen)
        _node(painter, .18, .32, size, fg, radius=size * .055)
        _node(painter, .18, .68, size, fg, radius=size * .055)
        painter.drawLine(
            QPointF(size * .30, size * .50),
            QPointF(size * .44, size * .50),
        )
        painter.drawLine(
            QPointF(size * .37, size * .43),
            QPointF(size * .37, size * .57),
        )
        painter.drawLine(
            QPointF(size * .53, size * .44),
            QPointF(size * .68, size * .44),
        )
        painter.drawLine(
            QPointF(size * .53, size * .56),
            QPointF(size * .68, size * .56),
        )
        _node(
            painter,
            .82,
            .50,
            size,
            muted,
            radius=size * .075,
            filled=False,
        )

    elif kind == IconKind.VISIBILITY:
        eye = QPainterPath()
        eye.moveTo(size * .10, size * .50)
        eye.cubicTo(
            size * .28,
            size * .22,
            size * .72,
            size * .22,
            size * .90,
            size * .50,
        )
        eye.cubicTo(
            size * .72,
            size * .78,
            size * .28,
            size * .78,
            size * .10,
            size * .50,
        )
        eye.closeSubpath()
        painter.drawPath(eye)
        _node(painter, .50, .50, size, fg, radius=size * .095)

    elif kind == IconKind.PREVIEW_DECK:
        _document(painter, size, muted)
        eye = QPainterPath()
        eye.moveTo(size * .34, size * .60)
        eye.cubicTo(
            size * .45,
            size * .46,
            size * .66,
            size * .46,
            size * .77,
            size * .60,
        )
        eye.cubicTo(
            size * .66,
            size * .74,
            size * .45,
            size * .74,
            size * .34,
            size * .60,
        )
        painter.setPen(pen)
        painter.drawPath(eye)
        _node(painter, .555, .60, size, fg, radius=size * .045)

    elif kind == IconKind.WRITE_DECK:
        _document(painter, size, muted)
        _arrow(
            painter,
            QPointF(size * .52, size * .53),
            QPointF(size * .82, size * .82),
            size,
            fg,
        )

    elif kind == IconKind.NEW_ANALYSIS:
        painter.setPen(QPen(muted, max(1.6, size / 20)))
        painter.drawPolyline(
            [
                QPointF(size * .12, size * .73),
                QPointF(size * .32, size * .73),
                QPointF(size * .32, size * .53),
                QPointF(size * .53, size * .53),
                QPointF(size * .53, size * .32),
                QPointF(size * .72, size * .32),
            ]
        )
        painter.setPen(pen)
        painter.drawLine(
            QPointF(size * .72, size * .18),
            QPointF(size * .90, size * .18),
        )
        painter.drawLine(
            QPointF(size * .81, size * .09),
            QPointF(size * .81, size * .27),
        )

    elif kind == IconKind.TOPOLOGY:
        cell = size * .14
        start_x = size * .16
        start_y = size * .19
        active = {
            (0, 0), (1, 0), (2, 0),
            (0, 1), (2, 1), (3, 1),
            (0, 2), (1, 2), (3, 2),
            (1, 3), (2, 3), (3, 3),
        }
        for row in range(4):
            for column in range(4):
                rect = QRectF(
                    start_x + column * cell,
                    start_y + row * cell,
                    cell * .88,
                    cell * .88,
                )
                if (column, row) in active:
                    painter.setBrush(
                        QColor(
                            fg.red(),
                            fg.green(),
                            fg.blue(),
                            70 + 25 * ((row + column) % 2),
                        )
                    )
                else:
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(
                    QPen(
                        fg if (column, row) in active else muted,
                        max(1.0, size / 32),
                    )
                )
                painter.drawRect(rect)
        painter.setBrush(Qt.BrushStyle.NoBrush)

    elif kind == IconKind.FILTER:
        funnel = QPainterPath()
        funnel.moveTo(size * .13, size * .20)
        funnel.lineTo(size * .87, size * .20)
        funnel.lineTo(size * .61, size * .50)
        funnel.lineTo(size * .61, size * .79)
        funnel.lineTo(size * .43, size * .88)
        funnel.lineTo(size * .43, size * .50)
        funnel.closeSubpath()
        painter.setBrush(soft)
        painter.drawPath(funnel)
        painter.setBrush(Qt.BrushStyle.NoBrush)

    elif kind == IconKind.THRESHOLD:
        painter.setPen(QPen(muted, max(2.0, size / 18)))
        painter.drawLine(
            QPointF(size * .14, size * .58),
            QPointF(size * .86, size * .58),
        )
        painter.setPen(pen)
        painter.drawLine(
            QPointF(size * .54, size * .24),
            QPointF(size * .54, size * .82),
        )
        _node(painter, .54, .58, size, fg, radius=size * .07)
        painter.setBrush(soft)
        painter.drawRect(QRectF(size * .55, size * .48, size * .30, size * .20))
        painter.setBrush(Qt.BrushStyle.NoBrush)

    elif kind == IconKind.JOB_MONITOR:
        painter.drawRoundedRect(
            QRectF(size * .12, size * .16, size * .76, size * .56),
            size * .04,
            size * .04,
        )
        painter.drawPolyline(
            [
                QPointF(size * .20, size * .52),
                QPointF(size * .34, size * .52),
                QPointF(size * .42, size * .34),
                QPointF(size * .53, size * .62),
                QPointF(size * .62, size * .43),
                QPointF(size * .79, size * .43),
            ]
        )
        painter.setPen(QPen(muted, max(1.4, size / 24)))
        painter.drawLine(
            QPointF(size * .50, size * .72),
            QPointF(size * .50, size * .86),
        )
        painter.drawLine(
            QPointF(size * .34, size * .86),
            QPointF(size * .66, size * .86),
        )

    elif kind == IconKind.UNDEFORMED:
        painter.setPen(
            QPen(
                muted,
                max(1.3, size / 25),
                Qt.PenStyle.DashLine,
            )
        )
        ghost = QPainterPath()
        ghost.moveTo(size * .12, size * .66)
        ghost.cubicTo(
            size * .34,
            size * .22,
            size * .62,
            size * .82,
            size * .88,
            size * .31,
        )
        painter.drawPath(ghost)
        painter.setPen(pen)
        painter.drawLine(
            QPointF(size * .12, size * .66),
            QPointF(size * .88, size * .66),
        )
        painter.drawLine(
            QPointF(size * .18, size * .60),
            QPointF(size * .18, size * .72),
        )
        painter.drawLine(
            QPointF(size * .82, size * .60),
            QPointF(size * .82, size * .72),
        )

    elif kind in {IconKind.QUERY_NODE, IconKind.QUERY_ELEMENT}:
        painter.setPen(QPen(fg, max(1.8, size / 18)))
        painter.drawEllipse(QRectF(size * .13, size * .13, size * .52, size * .52))
        painter.drawLine(
            QPointF(size * .57, size * .57),
            QPointF(size * .86, size * .86),
        )
        if kind == IconKind.QUERY_NODE:
            _node(painter, .39, .39, size, fg, radius=size * .065)
        else:
            painter.setBrush(soft)
            painter.drawRect(QRectF(size * .30, size * .30, size * .18, size * .18))
            painter.setBrush(Qt.BrushStyle.NoBrush)

    elif kind == IconKind.RANGE:
        painter.setPen(QPen(muted, max(1.5, size / 22)))
        painter.drawLine(
            QPointF(size * .50, size * .14),
            QPointF(size * .50, size * .86),
        )
        painter.setPen(pen)
        for y in (.28, .70):
            painter.drawLine(
                QPointF(size * .25, size * y),
                QPointF(size * .75, size * y),
            )
            _node(painter, .50, y, size, fg, radius=size * .055)

    painter.end()
    return QIcon(pixmap)
