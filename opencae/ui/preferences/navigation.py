from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QListWidget, QListWidgetItem


class PreferencesNavigation(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.setObjectName("PreferencesNavigation"); self.setFixedWidth(170); self.setSpacing(2)

    def add_page(self, title):
        item = QListWidgetItem(title); item.setSizeHint(QSize(150, 38)); self.addItem(item)
