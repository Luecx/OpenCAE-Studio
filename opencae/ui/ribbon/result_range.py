from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QDoubleSpinBox, QGridLayout, QLabel, QMenu, QToolButton, QWidget, QWidgetAction

from opencae.ui.core.icon_factory import IconKind, make_icon


class ResultRangeButton(QToolButton):
    range_changed = pyqtSignal(object)
    def __init__(self, parent=None):
        super().__init__(parent); self.setText("Range"); self.setIcon(make_icon(IconKind.RANGE, 28))
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup); self.setProperty("ribbonButton", True); self.setFixedSize(76, 70)
        self._data_range = (0.0, 1.0); panel = QWidget(); grid = QGridLayout(panel); grid.setContentsMargins(12, 10, 12, 10)
        self.minimum, self.minimum_auto = self._row(grid, 0, "Minimum")
        self.maximum, self.maximum_auto = self._row(grid, 1, "Maximum")
        menu = QMenu(self); action = QWidgetAction(menu); action.setDefaultWidget(panel); menu.addAction(action); self.setMenu(menu)
        for spin in (self.minimum, self.maximum): spin.valueChanged.connect(self._emit)
        self.minimum_auto.toggled.connect(lambda checked: self._auto_changed("minimum", checked))
        self.maximum_auto.toggled.connect(lambda checked: self._auto_changed("maximum", checked))
        self.minimum_auto.setChecked(True); self.maximum_auto.setChecked(True)

    @staticmethod
    def _row(layout, row, label):
        spin = QDoubleSpinBox(); spin.setRange(-1e300, 1e300); spin.setDecimals(8); spin.setMinimumWidth(150)
        auto = QToolButton(); auto.setText("Auto"); auto.setCheckable(True); auto.setMinimumWidth(52)
        layout.addWidget(QLabel(label), row, 0); layout.addWidget(spin, row, 1); layout.addWidget(auto, row, 2); return spin, auto

    def set_data_range(self, minimum, maximum):
        self._data_range = (float(minimum), float(maximum)); self._apply_auto("minimum"); self._apply_auto("maximum")

    def values(self):
        return {"minimum": self.minimum.value(), "maximum": self.maximum.value(),
                "minimum_auto": self.minimum_auto.isChecked(), "maximum_auto": self.maximum_auto.isChecked()}

    def _auto_changed(self, name, checked):
        getattr(self, name).setEnabled(not checked)
        if checked: self._apply_auto(name)
        self._emit()

    def _apply_auto(self, name):
        button = getattr(self, name + "_auto")
        if not button.isChecked(): return
        spin = getattr(self, name); spin.blockSignals(True); spin.setValue(self._data_range[0 if name == "minimum" else 1]); spin.blockSignals(False)

    def _emit(self, *_): self.range_changed.emit(self.values())
