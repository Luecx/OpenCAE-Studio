from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF
from PyQt6.QtWidgets import QWidget
from opencae.ui.core.theme import PALETTE


class ViewCube(QWidget):
    view_requested=pyqtSignal(str)
    def __init__(self,parent=None):
        super().__init__(parent); self.setFixedSize(112,118); self.setMouseTracking(True); self._hover=""
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground); self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing,True)
        p.setPen(QPen(QColor(PALETTE["border_light"]),1.2)); p.setBrush(QColor(27,32,38,225)); p.drawRoundedRect(QRectF(1,1,110,116),8,8)
        faces=self._faces()
        for name,poly in faces.items():
            active=name==self._hover; p.setPen(QPen(QColor(PALETTE["accent"] if active else PALETTE["border_light"]),1.2)); p.setBrush(QColor(PALETTE["panel_hover"] if active else PALETTE["panel_alt"])); p.drawPolygon(poly)
            p.setPen(QColor(PALETTE["text"])); p.drawText(poly.boundingRect(),Qt.AlignmentFlag.AlignCenter,name)
        p.setPen(QPen(QColor(PALETTE["border_light"]),1)); p.setBrush(QColor(PALETTE["panel_alt"])); p.drawEllipse(QRectF(40,88,32,22)); p.setPen(QColor(PALETTE["text"])); p.drawText(QRectF(40,88,32,22),Qt.AlignmentFlag.AlignCenter,"ISO")

    def mouseMoveEvent(self,event):
        self._hover=self._hit(event.position()); self.update()

    def leaveEvent(self,event): self._hover=""; self.update()

    def mousePressEvent(self,event):
        if event.button()!=Qt.MouseButton.LeftButton:return
        name=self._hit(event.position())
        if name:self.view_requested.emit(name)

    def _hit(self,point):
        if QRectF(40,88,32,22).contains(point):return "ISO"
        for name,poly in self._faces().items():
            if poly.containsPoint(point,Qt.FillRule.OddEvenFill):return name
        return ""

    @staticmethod
    def _faces():
        return {
            "TOP":QPolygonF((QPointF(28,28),QPointF(56,14),QPointF(85,28),QPointF(56,43))),
            "FRONT":QPolygonF((QPointF(28,28),QPointF(56,43),QPointF(56,76),QPointF(28,60))),
            "RIGHT":QPolygonF((QPointF(56,43),QPointF(85,28),QPointF(85,60),QPointF(56,76))),
        }
