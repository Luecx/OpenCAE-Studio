from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel

from opencae.ui.core.theme import PALETTE


RESULT_INFO_WIDTH = 340


class ResultSelectionPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ResultSelectionPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
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
        """Fill pixels outside the rounded panel with the VTK background color."""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(PALETTE["viewport"]))
        painter.end()
        super().paintEvent(event)

    def refresh_theme(self):
        self.setStyleSheet(
            f"QFrame#ResultSelectionPanel{{background:{PALETTE['overlay_bg']};"
            f"border:1px solid {PALETTE['overlay_border']};border-radius:7px;}}"
        )
        for title in self.titles:
            title.setStyleSheet(f"color:{PALETTE['muted']};font-size:8pt;")
        for value in self.values.values():
            value.setStyleSheet(f"color:{PALETTE['overlay_text']};font-weight:600;")

    def set_selection(self, values):
        for name, label in self.values.items():
            label.setText(str((values or {}).get(name) or "—"))
        self.adjustSize()
        self.show()
        self.raise_()

    def clear_selection(self):
        self.hide()
