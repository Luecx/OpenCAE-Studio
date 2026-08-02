from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel

from opencae.ui.core.theme import PALETTE


RESULT_INFO_WIDTH = 340


class ResultSelectionPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent); self.setObjectName("ResultSelectionPanel"); self.hide(); self.setFixedWidth(RESULT_INFO_WIDTH)
        self.setStyleSheet(f"QFrame#ResultSelectionPanel{{background:{PALETTE['panel']};border:1px solid {PALETTE['border_light']};border-radius:7px;}}")
        layout = QGridLayout(self); layout.setContentsMargins(10, 7, 10, 7); layout.setHorizontalSpacing(8); layout.setVerticalSpacing(2)
        self.values = {}
        for row, name in enumerate(("Step", "Frame", "Field", "Component")):
            title = QLabel(name); title.setStyleSheet(f"color:{PALETTE['muted']};font-size:8pt;")
            value = QLabel("—"); value.setStyleSheet(f"color:{PALETTE['text']};font-weight:600;")
            value.setWordWrap(True); layout.addWidget(title, row, 0); layout.addWidget(value, row, 1); self.values[name] = value
    def set_selection(self, values):
        for name, label in self.values.items(): label.setText(str((values or {}).get(name) or "—"))
        self.adjustSize(); self.show(); self.raise_()
    def clear_selection(self): self.hide()
