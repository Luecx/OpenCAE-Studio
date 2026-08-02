from PyQt6.QtWidgets import QHBoxLayout, QWidget

from .ribbon_group import RibbonGroup


class RibbonPage(QWidget):
    def __init__(self, groups, actions, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 0, 0)
        layout.setSpacing(0)
        for spec in groups:
            layout.addWidget(RibbonGroup(spec, actions))
        layout.addStretch(1)
