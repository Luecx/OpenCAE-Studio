from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QDoubleSpinBox, QFormLayout, QMenu, QPushButton, QToolButton, QWidget, QWidgetAction

from opencae.ui.core.icon_factory import IconKind
from .result_widgets import ribbon_button


class ResultDeformationButton(QToolButton):
    settings_changed = pyqtSignal()
    auto_requested = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent); template = ribbon_button("Deformed", IconKind.DEFORMATION, False)
        self.setText(template.text()); self.setIcon(template.icon()); self.setIconSize(template.iconSize())
        self.setToolButtonStyle(template.toolButtonStyle()); self.setProperty("ribbonButton", True); self.setFixedSize(82, 70)
        self.setCheckable(True); self.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        panel = QWidget(); form = QFormLayout(panel); form.setContentsMargins(12, 10, 12, 10)
        self.scale = QDoubleSpinBox(); self.scale.setRange(0.0, 1e12); self.scale.setDecimals(6); self.scale.setValue(1.0); self.scale.setMinimumWidth(155)
        reset = QPushButton("Reset to 1"); reset.clicked.connect(lambda: self.scale.setValue(1.0))
        auto = QPushButton("Auto"); auto.clicked.connect(self.auto_requested.emit)
        form.addRow("Deformation Scaling Factor", self.scale); form.addRow("", auto); form.addRow("", reset)
        menu = QMenu(self); action = QWidgetAction(menu); action.setDefaultWidget(panel); menu.addAction(action); self.setMenu(menu)
        self.toggled.connect(self.settings_changed.emit); self.scale.valueChanged.connect(self.settings_changed.emit)

    def values(self): return self.isChecked(), self.scale.value()

    def set_scale(self, value):
        self.scale.setValue(float(value))
