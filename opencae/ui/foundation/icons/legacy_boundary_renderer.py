from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainterPath, QPen, QPolygonF
from .legacy_kinds import IconKind
from .legacy_shapes import draw_cube


def _arrow(p, start, end, size):
    p.drawLine(start, end)
    dx, dy = end.x()-start.x(), end.y()-start.y(); length=max((dx*dx+dy*dy)**.5,1e-9)
    ux, uy = dx/length, dy/length; nx, ny = -uy, ux; h=size*.11
    p.drawLine(end, QPointF(end.x()-ux*h+nx*h*.55,end.y()-uy*h+ny*h*.55))
    p.drawLine(end, QPointF(end.x()-ux*h-nx*h*.55,end.y()-uy*h-ny*h*.55))


def draw_boundary_icon(p, kind, size, fg, muted, pen):
    if kind in {IconKind.FIXED, IconKind.DISPLACEMENT}:
        p.drawLine(QPointF(size*.16,size*.72),QPointF(size*.82,size*.72))
        for x in (.22,.36,.5,.64,.78): p.drawLine(QPointF(size*x,size*.72),QPointF(size*(x-.1),size*.86))
        _arrow(p,QPointF(size*.5,size*.18),QPointF(size*.5,size*.62),size); return True
    if kind in {IconKind.FORCE, IconKind.PRESSURE, IconKind.GRAVITY}:
        for x in ((.5,) if kind == IconKind.FORCE else (.25,.5,.75)):
            _arrow(p,QPointF(size*x,size*.14),QPointF(size*x,size*.72),size)
        return True
    if kind == IconKind.MOMENT: p.drawArc(QRectF(size*.18,size*.18,size*.64,size*.64),40*16,260*16); return True
    if kind == IconKind.TRACTION:
        p.drawLine(QPointF(size*.12,size*.72), QPointF(size*.88,size*.72))
        for x in (.28,.5,.72): _arrow(p,QPointF(size*(x-.12),size*.22),QPointF(size*(x+.08),size*.62),size)
        return True
    if kind == IconKind.VOLUME:
        draw_cube(p,QRectF(size*.08,size*.18,size*.52,size*.52),muted)
        _arrow(p,QPointF(size*.65,size*.72),QPointF(size*.9,size*.28),size)
        return True
    if kind == IconKind.INERTIA:
        p.setBrush(fg); p.drawEllipse(QRectF(size*.44,size*.44,size*.12,size*.12)); p.setBrush(Qt.BrushStyle.NoBrush)
        arc=QRectF(size*.18,size*.18,size*.64,size*.64); p.drawArc(arc,35*16,270*16)
        end=QPointF(size*.77,size*.25); back=QPointF(size*.67,size*.18); side=QPointF(size*.82,size*.13)
        p.setBrush(fg); p.drawPolygon(QPolygonF((end,back,side))); p.setBrush(Qt.BrushStyle.NoBrush); return True
    if kind == IconKind.TEMPERATURE:
        p.drawRoundedRect(QRectF(size*.42,size*.15,size*.16,size*.52),size*.08,size*.08); p.setBrush(fg)
        p.drawEllipse(QRectF(size*.31,size*.59,size*.38,size*.28)); p.drawRect(QRectF(size*.47,size*.3,size*.06,size*.38)); return True
    if kind == IconKind.SYMMETRY:
        p.setPen(QPen(muted,2,Qt.PenStyle.DashLine)); p.drawLine(QPointF(size*.5,size*.1),QPointF(size*.5,size*.9)); p.setPen(pen)
        p.drawPolyline([QPointF(size*.16,size*.28),QPointF(size*.38,size*.5),QPointF(size*.16,size*.72)])
        p.drawPolyline([QPointF(size*.84,size*.28),QPointF(size*.62,size*.5),QPointF(size*.84,size*.72)]); return True
    if kind == IconKind.REMOTE:
        p.drawEllipse(QRectF(size*.18,size*.18,size*.34,size*.34)); p.setBrush(fg); p.drawEllipse(QRectF(size*.29,size*.29,size*.12,size*.12)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(size*.43,size*.43),QPointF(size*.78,size*.76)); p.drawEllipse(QRectF(size*.7,size*.68,size*.18,size*.18)); return True
    return False
