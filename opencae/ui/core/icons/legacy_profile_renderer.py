from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QColor, QPainterPath
from .legacy_kinds import IconKind


def draw_profile_icon(p, kind, size, fg, muted, pen):
    p.setBrush(QColor(fg.red(),fg.green(),fg.blue(),45))
    if kind == IconKind.PROFILE_RECTANGLE: p.drawRect(QRectF(size*.2,size*.3,size*.6,size*.4)); return True
    if kind == IconKind.PROFILE_BOX:
        p.drawRect(QRectF(size*.16,size*.22,size*.68,size*.56)); p.setBrush(QColor("#20262d")); p.drawRect(QRectF(size*.3,size*.35,size*.4,size*.3)); return True
    if kind == IconKind.PROFILE_PIPE:
        p.drawEllipse(QRectF(size*.16,size*.16,size*.68,size*.68)); p.setBrush(QColor("#20262d")); p.drawEllipse(QRectF(size*.3,size*.3,size*.4,size*.4)); return True
    if kind == IconKind.PROFILE_I:
        path=QPainterPath(); path.moveTo(size*.18,size*.18); path.lineTo(size*.82,size*.18); path.lineTo(size*.82,size*.32); path.lineTo(size*.57,size*.32); path.lineTo(size*.57,size*.68); path.lineTo(size*.82,size*.68); path.lineTo(size*.82,size*.82); path.lineTo(size*.18,size*.82); path.lineTo(size*.18,size*.68); path.lineTo(size*.43,size*.68); path.lineTo(size*.43,size*.32); path.lineTo(size*.18,size*.32); path.closeSubpath(); p.drawPath(path); return True
    if kind == IconKind.PROFILE_CHANNEL:
        path=QPainterPath(); path.moveTo(size*.25,size*.18); path.lineTo(size*.78,size*.18); path.lineTo(size*.78,size*.32); path.lineTo(size*.42,size*.32); path.lineTo(size*.42,size*.68); path.lineTo(size*.78,size*.68); path.lineTo(size*.78,size*.82); path.lineTo(size*.25,size*.82); path.closeSubpath(); p.drawPath(path); return True
    if kind == IconKind.PROFILE_U:
        path=QPainterPath(); path.moveTo(size*.18,size*.2); path.lineTo(size*.34,size*.2); path.lineTo(size*.34,size*.68); path.lineTo(size*.66,size*.68); path.lineTo(size*.66,size*.2); path.lineTo(size*.82,size*.2); path.lineTo(size*.82,size*.82); path.lineTo(size*.18,size*.82); path.closeSubpath(); p.drawPath(path); return True
    if kind == IconKind.PROFILE_H:
        path=QPainterPath(); path.moveTo(size*.18,size*.16); path.lineTo(size*.34,size*.16); path.lineTo(size*.34,size*.42); path.lineTo(size*.66,size*.42); path.lineTo(size*.66,size*.16); path.lineTo(size*.82,size*.16); path.lineTo(size*.82,size*.84); path.lineTo(size*.66,size*.84); path.lineTo(size*.66,size*.58); path.lineTo(size*.34,size*.58); path.lineTo(size*.34,size*.84); path.lineTo(size*.18,size*.84); path.closeSubpath(); p.drawPath(path); return True
    if kind == IconKind.PROFILE_CIRCLE:
        p.setBrush(QColor(fg.red(),fg.green(),fg.blue(),45)); p.drawEllipse(QRectF(size*.18,size*.18,size*.64,size*.64)); return True
    if kind == IconKind.PROFILE_GENERAL:
        p.drawPolyline([QPointF(size*.16,size*.72),QPointF(size*.3,size*.28),QPointF(size*.56,size*.18),QPointF(size*.82,size*.52),QPointF(size*.68,size*.8)]); return True
    if kind == IconKind.PROFILE_GRAPH:
        p.drawLine(QPointF(size*.18,size*.82),QPointF(size*.18,size*.18)); p.drawLine(QPointF(size*.18,size*.82),QPointF(size*.84,size*.82)); p.drawPolyline([QPointF(size*.25,size*.7),QPointF(size*.4,size*.42),QPointF(size*.58,size*.58),QPointF(size*.78,size*.26)]); return True
    return False
