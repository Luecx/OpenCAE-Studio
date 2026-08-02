from __future__ import annotations

from enum import Enum
from PyQt6.QtCore import QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

from .theme import PALETTE


class IconKind(str, Enum):
    IMPORT = 'import'; SKETCH = 'sketch'; CREATE = 'create'; BOOLEAN = 'boolean'; SPLIT = 'split'; REPAIR = 'repair'
    ELEMENT = 'element'; SIZE = 'size'; LOCAL = 'local'; GENERATE = 'generate'; QUALITY = 'quality'
    NODE_SET = 'node_set'; ELEMENT_SET = 'element_set'; SURFACE = 'surface'; REFERENCE = 'reference'; CSYS = 'csys'
    MATERIAL = 'material'; SECTION = 'section'; ORIENTATION = 'orientation'; THICKNESS = 'thickness'; FORMULATION = 'formulation'
    INSTANCE = 'instance'; TRANSLATE = 'translate'; ROTATE = 'rotate'; ALIGN = 'align'; PATTERN = 'pattern'; INTERFERENCE = 'interference'
    FIXED = 'fixed'; DISPLACEMENT = 'displacement'; FORCE = 'force'; PRESSURE = 'pressure'; MOMENT = 'moment'; GRAVITY = 'gravity'
    ANALYSIS = 'analysis'; STEP = 'step'; CONTROLS = 'controls'; OUTPUT = 'output'; VALIDATE = 'validate'; RUN = 'run'
    CONTOUR = 'contour'; DEFORM = 'deform'; PROBE = 'probe'; ANIMATE = 'animate'; EXPORT = 'export'


def _cube(p: QPainter, r: QRectF, color: QColor) -> None:
    pen = QPen(color, 2)
    p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
    x, y, w, h = r.x(), r.y(), r.width(), r.height()
    a = QPointF(x + w*.2, y + h*.35); b = QPointF(x+w*.55, y+h*.18); c = QPointF(x+w*.82, y+h*.35)
    d = QPointF(x+w*.47, y+h*.53); e = QPointF(x+w*.2, y+h*.72); f = QPointF(x+w*.55, y+h*.9); g = QPointF(x+w*.82, y+h*.72)
    for u,v in [(a,b),(b,c),(c,d),(d,a),(a,e),(e,f),(f,d),(c,g),(g,f)]: p.drawLine(u,v)


def make_icon(kind: IconKind | str, size: int = 40, accent: str | None = None) -> QIcon:
    kind = IconKind(kind)
    pix = QPixmap(QSize(size, size)); pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    fg = QColor(accent or PALETTE['accent']); muted = QColor('#aab4bf'); white = QColor('#e5e9ef')
    r = QRectF(3, 3, size-6, size-6)
    pen = QPen(fg, max(1.6, size/20), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)

    if kind in {IconKind.IMPORT, IconKind.CREATE, IconKind.BOOLEAN, IconKind.SPLIT, IconKind.REPAIR, IconKind.ELEMENT, IconKind.ELEMENT_SET, IconKind.FORMULATION, IconKind.INSTANCE}:
        _cube(p, r, fg)
    if kind == IconKind.IMPORT:
        p.drawLine(QPointF(size*.18,size*.16), QPointF(size*.18,size*.47)); p.drawLine(QPointF(size*.18,size*.16), QPointF(size*.32,size*.29)); p.drawLine(QPointF(size*.18,size*.16), QPointF(size*.05,size*.29))
    elif kind == IconKind.SKETCH:
        path = QPainterPath(); path.moveTo(size*.15,size*.72); path.cubicTo(size*.28,size*.22,size*.55,size*.18,size*.75,size*.52); p.drawPath(path); p.drawLine(QPointF(size*.18,size*.77), QPointF(size*.74,size*.21))
    elif kind == IconKind.CREATE:
        p.drawLine(QPointF(size*.72,size*.12), QPointF(size*.72,size*.38)); p.drawLine(QPointF(size*.59,size*.25), QPointF(size*.85,size*.25))
    elif kind == IconKind.BOOLEAN:
        p.setBrush(QColor(fg.red(),fg.green(),fg.blue(),70)); p.drawEllipse(QRectF(size*.12,size*.2,size*.48,size*.48)); p.drawEllipse(QRectF(size*.4,size*.34,size*.48,size*.48))
    elif kind == IconKind.SPLIT:
        p.drawLine(QPointF(size*.12,size*.82), QPointF(size*.85,size*.12)); p.drawLine(QPointF(size*.55,size*.75), QPointF(size*.82,size*.75))
    elif kind == IconKind.REPAIR:
        p.drawArc(QRectF(size*.2,size*.12,size*.48,size*.48), 25*16, 250*16); p.drawLine(QPointF(size*.55,size*.54), QPointF(size*.82,size*.82)); p.drawEllipse(QRectF(size*.73,size*.73,size*.12,size*.12))
    elif kind == IconKind.SIZE:
        _cube(p, r, muted); p.setPen(pen); p.drawLine(QPointF(size*.14,size*.85),QPointF(size*.84,size*.85)); p.drawLine(QPointF(size*.14,size*.78),QPointF(size*.14,size*.92)); p.drawLine(QPointF(size*.84,size*.78),QPointF(size*.84,size*.92))
    elif kind == IconKind.LOCAL:
        _cube(p,r,muted); p.setBrush(fg); p.drawEllipse(QRectF(size*.57,size*.17,size*.17,size*.17)); p.setBrush(Qt.BrushStyle.NoBrush); p.drawEllipse(QRectF(size*.5,size*.1,size*.31,size*.31))
    elif kind == IconKind.GENERATE:
        for i in range(4):
            for j in range(4): p.drawRect(QRectF(size*(.13+i*.18),size*(.16+j*.18),size*.14,size*.14))
        p.drawLine(QPointF(size*.64,size*.12),QPointF(size*.87,size*.12)); p.drawLine(QPointF(size*.87,size*.12),QPointF(size*.8,size*.05))
    elif kind == IconKind.QUALITY or kind == IconKind.VALIDATE:
        _cube(p,r,muted); p.setPen(QPen(QColor(PALETTE['success']),3)); p.drawLine(QPointF(size*.54,size*.67),QPointF(size*.68,size*.8)); p.drawLine(QPointF(size*.68,size*.8),QPointF(size*.9,size*.49))
    elif kind == IconKind.NODE_SET:
        p.setBrush(fg)
        for x,y in [(0.25,.25),(.5,.2),(.72,.35),(.3,.58),(.58,.65),(.78,.78)]: p.drawEllipse(QRectF(size*x-3,size*y-3,6,6))
    elif kind == IconKind.ELEMENT_SET:
        for i in range(3):
            for j in range(3): p.drawRect(QRectF(size*(.17+i*.23),size*(.17+j*.23),size*.18,size*.18))
    elif kind == IconKind.SURFACE:
        path=QPainterPath(); path.moveTo(size*.12,size*.66); path.cubicTo(size*.3,size*.3,size*.65,size*.22,size*.88,size*.42); path.lineTo(size*.83,size*.71); path.cubicTo(size*.55,size*.52,size*.3,size*.58,size*.12,size*.82); path.closeSubpath(); p.setBrush(QColor(fg.red(),fg.green(),fg.blue(),60)); p.drawPath(path)
    elif kind == IconKind.REFERENCE:
        p.drawEllipse(QRectF(size*.28,size*.28,size*.44,size*.44)); p.drawLine(QPointF(size*.5,size*.08),QPointF(size*.5,size*.92)); p.drawLine(QPointF(size*.08,size*.5),QPointF(size*.92,size*.5)); p.setBrush(fg); p.drawEllipse(QRectF(size*.44,size*.44,size*.12,size*.12))
    elif kind in {IconKind.CSYS, IconKind.ORIENTATION, IconKind.TRANSLATE}:
        origin=QPointF(size*.34,size*.68); p.drawLine(origin,QPointF(size*.82,size*.68)); p.drawLine(origin,QPointF(size*.34,size*.18)); p.drawLine(origin,QPointF(size*.68,size*.38)); p.drawText(QRectF(size*.78,size*.58,12,12),'X'); p.drawText(QRectF(size*.27,size*.08,12,12),'Y')
    elif kind == IconKind.MATERIAL:
        p.setBrush(QColor(fg.red(),fg.green(),fg.blue(),80)); p.drawEllipse(QRectF(size*.12,size*.42,size*.32,size*.32)); p.drawEllipse(QRectF(size*.34,size*.18,size*.32,size*.32)); p.drawEllipse(QRectF(size*.56,size*.42,size*.32,size*.32))
    elif kind == IconKind.SECTION:
        path=QPainterPath(); path.moveTo(size*.22,size*.15); path.lineTo(size*.78,size*.15); path.lineTo(size*.78,size*.3); path.lineTo(size*.58,size*.3); path.lineTo(size*.58,size*.7); path.lineTo(size*.78,size*.7); path.lineTo(size*.78,size*.85); path.lineTo(size*.22,size*.85); path.lineTo(size*.22,size*.7); path.lineTo(size*.42,size*.7); path.lineTo(size*.42,size*.3); path.lineTo(size*.22,size*.3); path.closeSubpath(); p.setBrush(QColor(fg.red(),fg.green(),fg.blue(),80)); p.drawPath(path)
    elif kind == IconKind.THICKNESS:
        for y in [.28,.5,.72]: p.drawLine(QPointF(size*.18,size*y),QPointF(size*.82,size*y)); p.drawLine(QPointF(size*.85,size*.3),QPointF(size*.85,size*.7))
    elif kind == IconKind.ROTATE:
        p.drawArc(QRectF(size*.18,size*.18,size*.64,size*.64),25*16,285*16); p.drawLine(QPointF(size*.75,size*.2),QPointF(size*.88,size*.18)); p.drawLine(QPointF(size*.75,size*.2),QPointF(size*.8,size*.33))
    elif kind == IconKind.ALIGN:
        p.drawLine(QPointF(size*.2,size*.2),QPointF(size*.2,size*.8)); p.drawRect(QRectF(size*.3,size*.24,size*.28,size*.18)); p.drawRect(QRectF(size*.3,size*.58,size*.45,size*.18))
    elif kind == IconKind.PATTERN:
        for x,y in [(.25,.25),(.65,.25),(.25,.65),(.65,.65)]: _cube(p,QRectF(size*x-9,size*y-9,18,18),fg)
    elif kind in {IconKind.FIXED, IconKind.DISPLACEMENT}:
        p.drawLine(QPointF(size*.16,size*.72),QPointF(size*.82,size*.72));
        for x in [.22,.36,.5,.64,.78]: p.drawLine(QPointF(size*x,size*.72),QPointF(size*(x-.1),size*.86))
        p.drawLine(QPointF(size*.5,size*.18),QPointF(size*.5,size*.62))
    elif kind in {IconKind.FORCE, IconKind.PRESSURE, IconKind.GRAVITY}:
        xs=[.5] if kind==IconKind.FORCE else [.25,.5,.75]
        for x in xs:
            p.drawLine(QPointF(size*x,size*.14),QPointF(size*x,size*.72)); p.drawLine(QPointF(size*x,size*.72),QPointF(size*(x-.08),size*.58)); p.drawLine(QPointF(size*x,size*.72),QPointF(size*(x+.08),size*.58))
    elif kind == IconKind.MOMENT:
        p.drawArc(QRectF(size*.18,size*.18,size*.64,size*.64),40*16,260*16)
    elif kind in {IconKind.ANALYSIS, IconKind.CONTROLS}:
        for y,w in [(.28,.5),(.5,.68),(.72,.38)]: p.drawLine(QPointF(size*.18,size*y),QPointF(size*(.18+w),size*y)); p.setBrush(fg); p.drawEllipse(QRectF(size*(.18+w)-3,size*y-3,6,6))
    elif kind == IconKind.STEP:
        p.drawPolyline([QPointF(size*.15,size*.75),QPointF(size*.36,size*.75),QPointF(size*.36,size*.54),QPointF(size*.58,size*.54),QPointF(size*.58,size*.32),QPointF(size*.82,size*.32)])
    elif kind == IconKind.OUTPUT:
        p.drawRect(QRectF(size*.18,size*.18,size*.64,size*.64)); p.drawPolyline([QPointF(size*.25,size*.68),QPointF(size*.4,size*.48),QPointF(size*.55,size*.58),QPointF(size*.75,size*.28)])
    elif kind == IconKind.RUN:
        p.setBrush(fg); path=QPainterPath(); path.moveTo(size*.3,size*.18); path.lineTo(size*.78,size*.5); path.lineTo(size*.3,size*.82); path.closeSubpath(); p.drawPath(path)
    elif kind == IconKind.CONTOUR:
        for i,c in enumerate(['#375fc7','#31a6d8','#49bd79','#e5c64a','#e46545']): p.setPen(QPen(QColor(c),4)); p.drawArc(QRectF(size*(.12+i*.05),size*(.15+i*.05),size*(.75-i*.1),size*(.62-i*.1)),20*16,220*16)
    elif kind == IconKind.DEFORM:
        p.drawLine(QPointF(size*.12,size*.65),QPointF(size*.88,size*.65)); path=QPainterPath(); path.moveTo(size*.12,size*.65); path.cubicTo(size*.35,size*.15,size*.62,size*.85,size*.88,size*.28); p.drawPath(path)
    elif kind == IconKind.PROBE:
        p.drawEllipse(QRectF(size*.18,size*.18,size*.5,size*.5)); p.drawLine(QPointF(size*.58,size*.58),QPointF(size*.84,size*.84)); p.setBrush(fg); p.drawEllipse(QRectF(size*.38,size*.38,size*.1,size*.1))
    elif kind == IconKind.ANIMATE:
        p.setBrush(fg); path=QPainterPath(); path.moveTo(size*.36,size*.22); path.lineTo(size*.76,size*.5); path.lineTo(size*.36,size*.78); path.closeSubpath(); p.drawPath(path)
    elif kind == IconKind.EXPORT:
        p.drawRect(QRectF(size*.2,size*.38,size*.6,size*.46)); p.drawLine(QPointF(size*.5,size*.1),QPointF(size*.5,size*.56)); p.drawLine(QPointF(size*.5,size*.1),QPointF(size*.36,size*.26)); p.drawLine(QPointF(size*.5,size*.1),QPointF(size*.64,size*.26))
    p.end(); return QIcon(pix)
