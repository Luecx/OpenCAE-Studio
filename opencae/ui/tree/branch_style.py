from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QProxyStyle, QStyle
from opencae.ui.core.theme import PALETTE


class TreeBranchStyle(QProxyStyle):
    def drawPrimitive(self,element,option,painter,widget=None):
        if element!=QStyle.PrimitiveElement.PE_IndicatorBranch:return super().drawPrimitive(element,option,painter,widget)
        if not option.state&QStyle.StateFlag.State_Children:return
        center=option.rect.center(); cx,cy=float(center.x()),float(center.y()); opened=bool(option.state&QStyle.StateFlag.State_Open)
        hovered=bool(option.state&QStyle.StateFlag.State_MouseOver); selected=bool(option.state&QStyle.StateFlag.State_Selected)
        color=PALETTE["accent"] if selected else (PALETTE["text"] if hovered else PALETTE["muted"])
        painter.save(); painter.setRenderHint(QPainter.RenderHint.Antialiasing,True); painter.setPen(QPen(QColor(color),1.15)); painter.setBrush(QColor(color))
        points=QPolygonF((QPointF(cx-3.4,cy-1.5),QPointF(cx+3.4,cy-1.5),QPointF(cx,cy+2.8))) if opened else QPolygonF((QPointF(cx-1.5,cy-3.4),QPointF(cx-1.5,cy+3.4),QPointF(cx+2.8,cy)))
        painter.drawPolygon(points); painter.restore()
