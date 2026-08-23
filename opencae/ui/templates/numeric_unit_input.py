"""Provides the canonical numeric input with an optional fixed unit segment."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QDoubleSpinBox, QHBoxLayout, QLabel, QWidget

from .control_metrics import apply_primary_control_height


class NumericUnitInput(QWidget):
    """Edit a scalar value while rendering its unit as a non-editable right cell."""

    valueChanged = pyqtSignal(float)

    def __init__(
        self,
        value: float = 0.0,
        unit: str = "",
        *,
        minimum: float = -1e30,
        maximum: float = 1e30,
        decimals: int = 8,
        parent=None,
    ):
        """Build one scalar editor and optional fixed unit cell."""
        super().__init__(parent)
        self.setObjectName("NumericUnitInput")
        self.setMinimumWidth(0)
        apply_primary_control_height(self)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self.editor = QDoubleSpinBox()
        self.editor.setMinimumWidth(0)
        self.editor.setRange(minimum, maximum)
        self.editor.setDecimals(decimals)
        self.editor.setValue(float(value))
        apply_primary_control_height(self.editor)
        self.editor.valueChanged.connect(self.valueChanged.emit)
        self._layout.addWidget(self.editor, 1)

        self.unit_label = None
        self.setUnit(unit)

    def value(self) -> float:
        """Return the current scalar value."""
        return self.editor.value()

    def setValue(self, value: float) -> None:
        """Replace the current scalar value."""
        self.editor.setValue(float(value))

    def setRange(self, minimum: float, maximum: float) -> None:
        """Replace the accepted numeric range."""
        self.editor.setRange(minimum, maximum)

    def setDecimals(self, decimals: int) -> None:
        """Replace the number of displayed decimal places."""
        self.editor.setDecimals(decimals)

    def setUnit(self, unit: str) -> None:
        """Replace the fixed unit segment without rebuilding the numeric editor."""
        text = str(unit or "").strip()
        if self.unit_label is not None and not text:
            self._layout.removeWidget(self.unit_label)
            self.unit_label.deleteLater()
            self.unit_label = None
        elif self.unit_label is None and text:
            self.unit_label = QLabel(text)
            self.unit_label.setObjectName("PrimaryUnitLabel")
            self.unit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            apply_primary_control_height(self.unit_label)
            self._layout.addWidget(self.unit_label)
        elif self.unit_label is not None:
            self.unit_label.setText(text)

        self.editor.setObjectName(
            "PrimaryNumericWithUnit" if self.unit_label is not None else "PrimaryNumeric"
        )
        # Object-name selectors determine the joined border geometry. Repolish
        # immediately when a method switches between dimensionless and unitful.
        style = self.editor.style()
        style.unpolish(self.editor)
        style.polish(self.editor)
        self.editor.update()

    def setSuffix(self, suffix: str) -> None:
        """Compatibility alias mapping legacy spin-box suffix calls to a unit cell."""
        self.setUnit(str(suffix or "").strip())
