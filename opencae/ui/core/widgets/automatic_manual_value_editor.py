"""Provides a reusable editor for automatic-factor or manual-distance values."""

from __future__ import annotations

from PyQt6.QtWidgets import QRadioButton, QVBoxLayout, QWidget

from opencae.ui.templates import NumericUnitInput, field_block


class AutomaticManualValueEditor(QWidget):
    """Edit a value as either factor times a reference scale or an absolute value."""

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
        """Build automatic/manual mode choices with canonical numeric fields."""
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.automatic = QRadioButton(automatic_text)
        self.manual = QRadioButton(manual_text)
        self.factor = NumericUnitInput(
            factor,
            "",
            minimum=float(factor_range[0]),
            maximum=float(factor_range[1]),
            decimals=int(factor_decimals),
        )
        self.value = NumericUnitInput(
            max(float(value), float(value_range[0])),
            "",
            minimum=float(value_range[0]),
            maximum=float(value_range[1]),
            decimals=int(value_decimals),
        )

        self.automatic.setChecked(bool(automatic))
        self.manual.setChecked(not bool(automatic))
        self.automatic.toggled.connect(self._sync_enabled)
        self.manual.toggled.connect(self._sync_enabled)

        layout.addWidget(self.automatic)
        layout.addWidget(field_block(factor_label, self.factor))
        layout.addWidget(self.manual)
        layout.addWidget(field_block(value_label, self.value))
        self._sync_enabled()

    def values(self) -> tuple[bool, float, float]:
        """Return automatic mode, factor and absolute value."""
        return (
            self.automatic.isChecked(),
            self.factor.value(),
            self.value.value(),
        )

    def _sync_enabled(self, *_):
        """Enable only the numeric field that belongs to the selected mode."""
        self.factor.setEnabled(self.automatic.isChecked())
        self.value.setEnabled(self.manual.isChecked())
