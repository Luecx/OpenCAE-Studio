"""Provides a reusable editor for automatic-factor or manual-distance values."""

from PyQt6.QtWidgets import QDoubleSpinBox, QFormLayout, QRadioButton, QWidget


class AutomaticManualValueEditor(QWidget):
    """Edits a value as either factor times a reference scale or an absolute value."""

    def __init__(
        self,
        *,
        automatic=True,
        factor=1.0,
        value=0.0,
        automatic_text="Automatic",
        factor_label="Factor",
        manual_text="Manual",
        value_label="Value",
        factor_range=(1.0e-12, 1.0e12),
        value_range=(1.0e-12, 1.0e30),
        factor_decimals=6,
        value_decimals=9,
        parent=None,
    ):
        super().__init__(parent)
        layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(18)
        layout.setVerticalSpacing(8)

        self.automatic = QRadioButton(automatic_text)
        self.manual = QRadioButton(manual_text)
        self.factor = QDoubleSpinBox()
        self.factor.setDecimals(int(factor_decimals))
        self.factor.setRange(*map(float, factor_range))
        self.factor.setValue(float(factor))
        self.value = QDoubleSpinBox()
        self.value.setDecimals(int(value_decimals))
        self.value.setRange(*map(float, value_range))
        self.value.setValue(max(float(value), float(value_range[0])))

        self.automatic.setChecked(bool(automatic))
        self.manual.setChecked(not bool(automatic))
        self.automatic.toggled.connect(self._sync_enabled)
        self.manual.toggled.connect(self._sync_enabled)

        layout.addRow(self.automatic)
        layout.addRow(factor_label, self.factor)
        layout.addRow(self.manual)
        layout.addRow(value_label, self.value)
        self._sync_enabled()

    def values(self) -> tuple[bool, float, float]:
        """Return automatic mode, factor and absolute value."""

        return (
            self.automatic.isChecked(),
            self.factor.value(),
            self.value.value(),
        )

    def _sync_enabled(self, *_):
        self.factor.setEnabled(self.automatic.isChecked())
        self.value.setEnabled(self.manual.isChecked())
