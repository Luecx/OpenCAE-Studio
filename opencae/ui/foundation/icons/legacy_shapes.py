from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen


def draw_cube(painter: QPainter, rect: QRectF, color: QColor) -> None:
    painter.setPen(QPen(color, 2))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    x, y, width, height = rect.x(), rect.y(), rect.width(), rect.height()
    a = QPointF(x + width * .2, y + height * .35)
    b = QPointF(x + width * .55, y + height * .18)
    c = QPointF(x + width * .82, y + height * .35)
    d = QPointF(x + width * .47, y + height * .53)
    e = QPointF(x + width * .2, y + height * .72)
    f = QPointF(x + width * .55, y + height * .9)
    g = QPointF(x + width * .82, y + height * .72)
    for start, end in ((a, b), (b, c), (c, d), (d, a), (a, e), (e, f), (f, d), (c, g), (g, f)):
        painter.drawLine(start, end)
