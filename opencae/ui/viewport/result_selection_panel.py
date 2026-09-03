from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel

from opencae.ui.core.theme import PALETTE


RESULT_INFO_WIDTH = 340


class ResultSelectionPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ResultSelectionPanel")
        self.hide()
        self.setFixedWidth(RESULT_INFO_WIDTH)
        layout = QGridLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(2)
        self.values = {}
        self.titles = []
        for row, name in enumerate(("Step", "Frame", "Field", "Component")):
            title = QLabel(name)
            value = QLabel("—")
            value.setWordWrap(True)
            layout.addWidget(title, row, 0)
            layout.addWidget(value, row, 1)
            self.titles.append(title)
            self.values[name] = value
        self.refresh_theme()

    def paintEvent(self, event) -> None:
        """Paint a rounded panel over a viewport-colored rectangular backing."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(PALETTE["viewport"]))
        painter.setBrush(QColor(PALETTE["overlay_bg"]))
        painter.setPen(QPen(QColor(PALETTE["overlay_border"]), 1.0))
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.drawRoundedRect(rect, 7.0, 7.0)

    def refresh_theme(self):
        for title in self.titles:
            title.setStyleSheet(f"color:{PALETTE['muted']};font-size:8pt;")
        for value in self.values.values():
            value.setStyleSheet(f"color:{PALETTE['overlay_text']};font-weight:600;")
        self.update()

    def set_selection(self, values):
        for name, label in self.values.items():
            label.setText(str((values or {}).get(name) or "—"))
        self.adjustSize()
        self.show()
        self.raise_()

    def clear_selection(self):
        self.hide()
