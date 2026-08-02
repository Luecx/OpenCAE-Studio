from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QPainterPath
from .legacy_kinds import IconKind


def draw_analysis_icon(p, kind, size, fg, muted, pen):
    if kind == IconKind.STEP_LINEAR:
        p.drawLine(QPointF(size*.16,size*.76),QPointF(size*.84,size*.24)); p.drawLine(QPointF(size*.16,size*.76),QPointF(size*.84,size*.76)); return True
    if kind == IconKind.STEP_NONLINEAR:
        path=QPainterPath(); path.moveTo(size*.14,size*.76); path.cubicTo(size*.32,size*.72,size*.35,size*.25,size*.82,size*.22); p.drawPath(path); p.drawLine(QPointF(size*.14,size*.76),QPointF(size*.84,size*.76)); return True
    if kind == IconKind.STEP_MODAL:
        path=QPainterPath(); path.moveTo(size*.12,size*.55); path.cubicTo(size*.28,size*.18,size*.42,size*.82,size*.58,size*.45); path.cubicTo(size*.7,size*.18,size*.78,size*.66,size*.88,size*.36); p.drawPath(path); return True
    if kind == IconKind.STEP_BUCKLING:
        p.drawLine(QPointF(size*.22,size*.16),QPointF(size*.22,size*.84)); path=QPainterPath(); path.moveTo(size*.22,size*.16); path.cubicTo(size*.72,size*.28,size*.28,size*.62,size*.78,size*.84); p.drawPath(path); return True
    if kind == IconKind.STEP_TRANSIENT:
        p.drawLine(QPointF(size*.14,size*.78),QPointF(size*.86,size*.78)); p.drawPolyline([QPointF(size*.18,size*.62),QPointF(size*.36,size*.62),QPointF(size*.36,size*.34),QPointF(size*.58,size*.34),QPointF(size*.58,size*.2),QPointF(size*.82,size*.2)]); return True
    if kind == IconKind.REORDER:
        for y in (.28,.5,.72): p.drawLine(QPointF(size*.28,size*y),QPointF(size*.78,size*y))
        p.drawLine(QPointF(size*.16,size*.25),QPointF(size*.16,size*.75)); p.drawLine(QPointF(size*.16,size*.25),QPointF(size*.1,size*.34)); p.drawLine(QPointF(size*.16,size*.25),QPointF(size*.22,size*.34)); return True
    if kind == IconKind.MATRIX:
        for i in range(3):
            for j in range(3): p.drawRect(QRectF(size*(.18+i*.22),size*(.18+j*.22),size*.16,size*.16))
        return True
    return False
