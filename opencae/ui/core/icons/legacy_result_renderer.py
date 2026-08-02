from PyQt6.QtCore import QPointF,QRectF,Qt
from PyQt6.QtGui import QColor,QPen
from .legacy_kinds import IconKind


def draw_result_icon(p,kind,size,fg,muted,pen):
    if kind==IconKind.RESULT_STEP:
        p.drawPolyline([QPointF(size*.16,size*.72),QPointF(size*.36,size*.72),QPointF(size*.36,size*.5),QPointF(size*.58,size*.5),QPointF(size*.58,size*.28),QPointF(size*.84,size*.28)]); return True
    if kind==IconKind.RESULT_FRAME:
        p.drawRect(QRectF(size*.16,size*.2,size*.68,size*.58)); p.drawLine(QPointF(size*.3,size*.12),QPointF(size*.3,size*.86)); p.drawLine(QPointF(size*.7,size*.12),QPointF(size*.7,size*.86)); return True
    if kind==IconKind.MESH_LINES:
        for i in range(4):
            p.drawLine(QPointF(size*.15,size*(.18+i*.18)),QPointF(size*.85,size*(.18+i*.18)))
            p.drawLine(QPointF(size*(.15+i*.23),size*.18),QPointF(size*(.15+i*.23),size*.72))
        return True
    if kind==IconKind.BOUNDARY_LINES:
        p.setPen(QPen(fg,max(2,size/14))); p.drawRoundedRect(QRectF(size*.16,size*.18,size*.68,size*.62),4,4); return True
    if kind==IconKind.DEFORMATION:
        p.setPen(QPen(muted,max(1.4,size/24),Qt.PenStyle.DashLine)); p.drawLine(QPointF(size*.12,size*.66),QPointF(size*.88,size*.66))
        p.setPen(pen); path=__import__('PyQt6.QtGui',fromlist=['QPainterPath']).QPainterPath(); path.moveTo(size*.12,size*.66); path.cubicTo(size*.34,size*.14,size*.62,size*.84,size*.88,size*.28); p.drawPath(path); return True
    return False
