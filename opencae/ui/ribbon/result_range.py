"""Provides the result contour-range ribbon control and its compact editor flyout."""

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QMenu,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from opencae.ui.core.icon_factory import IconKind, make_icon
from opencae.ui.templates import (
    PRIMARY_CONTROL_HEIGHT,
    apply_primary_control_height,
    field_block,
)


class ResultRangeButton(QToolButton):
    """Open a compact editor for automatic or manual contour limits."""

    range_changed = pyqtSignal(object)

    def __init__(self, parent=None):
        """Build the ribbon button and its shared-metric minimum/maximum controls."""
        super().__init__(parent)
        self.setText("Contour")
        self.setIcon(make_icon(IconKind.RANGE, 28))
        self.setIconSize(QSize(28, 28))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setProperty("ribbonButton", True)
        self.setFixedSize(82, 70)
        self._data_range = (0.0, 1.0)

        panel = QWidget()
        panel.setMinimumWidth(300)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)
        minimum_row, self.minimum, self.minimum_auto = self._field()
        maximum_row, self.maximum, self.maximum_auto = self._field()
        layout.addWidget(field_block("Minimum", minimum_row))
        layout.addWidget(field_block("Maximum", maximum_row))

        menu = QMenu(self)
        action = QWidgetAction(menu)
        action.setDefaultWidget(panel)
        menu.addAction(action)
        self.setMenu(menu)

        for spin in (self.minimum, self.maximum):
            spin.valueChanged.connect(self._emit)
        self.minimum_auto.toggled.connect(
            lambda checked: self._auto_changed("minimum", checked)
        )
        self.maximum_auto.toggled.connect(
            lambda checked: self._auto_changed("maximum", checked)
        )
        self.minimum_auto.setChecked(True)
        self.maximum_auto.setChecked(True)

    @staticmethod
    def _field():
        """Return one composite numeric limit row and its child controls."""
        host = QWidget()
        row = QHBoxLayout(host)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        spin = QDoubleSpinBox()
        spin.setRange(-1e300, 1e300)
        spin.setDecimals(8)
        spin.setMinimumWidth(0)
        apply_primary_control_height(spin)

        auto = QToolButton()
        auto.setText("Auto")
        auto.setCheckable(True)
        auto.setFixedHeight(PRIMARY_CONTROL_HEIGHT)
        auto.setMinimumWidth(58)
        auto.setObjectName("ResultAutoButton")

        row.addWidget(spin, 1)
        row.addWidget(auto)
        return host, spin, auto

    def set_data_range(self, minimum, maximum):
        """Replace the automatic limits with the range of the active result field."""
        self._data_range = (float(minimum), float(maximum))
        self._apply_auto("minimum")
        self._apply_auto("maximum")

    def values(self):
        """Return manual values together with both automatic-mode flags."""
        return {
            "minimum": self.minimum.value(),
            "maximum": self.maximum.value(),
            "minimum_auto": self.minimum_auto.isChecked(),
            "maximum_auto": self.maximum_auto.isChecked(),
        }

    def _auto_changed(self, name, checked):
        """Enable manual editing only when automatic range selection is disabled."""
        getattr(self, name).setEnabled(not checked)
        if checked:
            self._apply_auto(name)
        self._emit()

    def _apply_auto(self, name):
        """Copy the current data-range endpoint into an automatic limit editor."""
        button = getattr(self, name + "_auto")
        if not button.isChecked():
            return
        spin = getattr(self, name)
        spin.blockSignals(True)
        spin.setValue(self._data_range[0 if name == "minimum" else 1])
        spin.blockSignals(False)

    def _emit(self, *_):
        """Publish the complete contour-range configuration."""
        self.range_changed.emit(self.values())
