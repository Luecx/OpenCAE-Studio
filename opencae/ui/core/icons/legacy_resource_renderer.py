from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainterPath, QPen
from .legacy_kinds import IconKind


def draw_resource_icon(p, kind, size, fg, muted, pen):
    if kind == IconKind.ASSIGN_SECTION:
        # Meshed region receiving an I-shaped section: assignment is the visual action.
        for i in range(2):
            for j in range(2):
                p.setBrush(QColor(fg.red(),fg.green(),fg.blue(),55 if (i+j)%2 else 100))
                p.drawRect(QRectF(size*(.10+i*.22),size*(.42+j*.22),size*.19,size*.19))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(size*.58,size*.14,size*.30,size*.08)); p.drawRect(QRectF(size*.69,size*.22,size*.08,size*.28)); p.drawRect(QRectF(size*.58,size*.50,size*.30,size*.08))
        p.drawLine(QPointF(size*.48,size*.34),QPointF(size*.66,size*.43)); p.drawLine(QPointF(size*.66,size*.43),QPointF(size*.58,size*.30)); p.drawLine(QPointF(size*.66,size*.43),QPointF(size*.51,size*.50))
        return True
    if kind == IconKind.ELASTICITY:
        p.drawLine(QPointF(size*.18,size*.55),QPointF(size*.82,size*.55))
        for x in (.26,.38,.5,.62,.74): p.drawEllipse(QRectF(size*x-3,size*.55-3,6,6))
        p.drawLine(QPointF(size*.16,size*.3),QPointF(size*.16,size*.8)); p.drawLine(QPointF(size*.84,size*.3),QPointF(size*.84,size*.8)); return True
    if kind == IconKind.DENSITY:
        p.setBrush(QColor(fg.red(),fg.green(),fg.blue(),85)); p.drawEllipse(QRectF(size*.2,size*.2,size*.6,size*.6));
        for x,y in ((.35,.38),(.58,.34),(.45,.58),(.65,.62)): p.setBrush(fg); p.drawEllipse(QRectF(size*x-2,size*y-2,4,4))
        return True
    if kind == IconKind.PLASTICITY:
        path=QPainterPath(); path.moveTo(size*.15,size*.78); path.lineTo(size*.45,size*.45); path.lineTo(size*.8,size*.3); p.drawPath(path)
        p.drawLine(QPointF(size*.15,size*.78),QPointF(size*.82,size*.78)); p.drawLine(QPointF(size*.15,size*.78),QPointF(size*.15,size*.18)); return True
    if kind == IconKind.THERMAL:
        p.drawRoundedRect(QRectF(size*.42,size*.14,size*.16,size*.52),size*.08,size*.08); p.setBrush(fg)
        p.drawEllipse(QRectF(size*.31,size*.58,size*.38,size*.28)); p.drawRect(QRectF(size*.47,size*.3,size*.06,size*.38)); return True
    if kind == IconKind.FIELD:
        for i,c in enumerate(("#356bc2","#32a6c8","#59be75","#e1c54a")):
            p.setPen(QPen(QColor(c),3)); p.drawArc(QRectF(size*(.12+i*.06),size*(.16+i*.05),size*(.76-i*.12),size*(.62-i*.1)),20*16,220*16)
        return True
    if kind in {IconKind.SECTION_SOLID,IconKind.SECTION_SHELL,IconKind.SECTION_BEAM,IconKind.SECTION_TRUSS}:
        if kind == IconKind.SECTION_SOLID:
            p.setBrush(QColor(fg.red(),fg.green(),fg.blue(),70)); p.drawRect(QRectF(size*.2,size*.2,size*.6,size*.6))
        elif kind == IconKind.SECTION_SHELL:
            for y in (.38,.5,.62): p.drawLine(QPointF(size*.16,size*y),QPointF(size*.84,size*y))
        elif kind == IconKind.SECTION_BEAM:
            p.drawRect(QRectF(size*.18,size*.18,size*.64,size*.14)); p.drawRect(QRectF(size*.43,size*.32,size*.14,size*.36)); p.drawRect(QRectF(size*.18,size*.68,size*.64,size*.14))
        else:
            p.drawLine(QPointF(size*.18,size*.5),QPointF(size*.82,size*.5)); p.setBrush(fg); p.drawEllipse(QRectF(size*.43,size*.43,size*.14,size*.14))
        return True
    return False
