from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainterPath, QPen
from .legacy_kinds import IconKind


def _node(p, x, y, size, color):
    p.setBrush(color); p.drawEllipse(QRectF(size*x-3, size*y-3, 6, 6)); p.setBrush(Qt.BrushStyle.NoBrush)

def draw_constraint_icon(p, kind, size, fg, muted, pen):
    if kind == IconKind.CONSTRAINT_KINEMATIC:
        _node(p,.24,.5,size,fg); _node(p,.76,.28,size,muted); _node(p,.76,.72,size,muted)
        p.drawLine(QPointF(size*.27,size*.5),QPointF(size*.72,size*.3)); p.drawLine(QPointF(size*.27,size*.5),QPointF(size*.72,size*.7)); return True
    if kind == IconKind.CONSTRAINT_DISTRIBUTING:
        _node(p,.24,.5,size,fg)
        for y in (.22,.4,.6,.78):
            _node(p,.78,y,size,muted); p.drawLine(QPointF(size*.28,size*.5),QPointF(size*.74,size*y))
        return True
    if kind == IconKind.CONSTRAINT_TIE:
        p.drawLine(QPointF(size*.15,size*.32),QPointF(size*.85,size*.32)); p.drawLine(QPointF(size*.15,size*.68),QPointF(size*.85,size*.68))
        for x in (.28,.5,.72): p.drawLine(QPointF(size*x,size*.32),QPointF(size*x,size*.68))
        return True
    if kind == IconKind.CONSTRAINT_RIGID:
        p.setBrush(QColor(fg.red(),fg.green(),fg.blue(),55)); p.drawRect(QRectF(size*.18,size*.22,size*.64,size*.56)); p.setBrush(Qt.BrushStyle.NoBrush)
        _node(p,.5,.5,size,fg); p.drawLine(QPointF(size*.5,size*.5),QPointF(size*.24,size*.28)); p.drawLine(QPointF(size*.5,size*.5),QPointF(size*.76,size*.72)); return True
    if kind == IconKind.CONSTRAINT_EQUATION:
        p.drawText(QRectF(size*.08,size*.24,size*.84,size*.52),Qt.AlignmentFlag.AlignCenter,"Σ aᵢuᵢ=0"); return True
    if kind == IconKind.CONSTRAINT_MPC:
        for x,y in ((.22,.28),(.22,.72),(.78,.28),(.78,.72)):_node(p,x,y,size,fg if x<.5 else muted)
        p.drawLine(QPointF(size*.26,size*.28),QPointF(size*.74,size*.72)); p.drawLine(QPointF(size*.26,size*.72),QPointF(size*.74,size*.28)); return True
    return False
