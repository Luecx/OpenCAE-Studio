"""Numeric form control with an optional fixed unit segment."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QWidget

from opencae.ui.primitives.inputs.input_form_number import InputFormNumber
from opencae.ui.primitives.labels import LabelBody
from opencae.ui.primitives.inputs.geometry import apply_primary_input_geometry


class ControlNumericUnit(QWidget):
    """Compose one numeric primitive and one optional non-editable unit label."""

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
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ControlNumericUnit")
        self.setMinimumWidth(0)
        apply_primary_input_geometry(self)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self.editor = InputFormNumber(
            value,
            minimum=minimum,
            maximum=maximum,
            decimals=decimals,
        )
        self.editor.valueChanged.connect(self.valueChanged.emit)
        self._layout.addWidget(self.editor, 1)
        self.unit_label = None
        self.setUnit(unit)

    def value(self) -> float:
        return self.editor.value()

    def setValue(self, value: float) -> None:
        self.editor.setValue(float(value))

    def setRange(self, minimum: float, maximum: float) -> None:
        self.editor.setRange(minimum, maximum)

    def setDecimals(self, decimals: int) -> None:
        self.editor.setDecimals(int(decimals))

    def setUnit(self, unit: str) -> None:
        text = str(unit or "").strip()
        if self.unit_label is not None and not text:
            self._layout.removeWidget(self.unit_label)
            self.unit_label.deleteLater()
            self.unit_label = None
        elif self.unit_label is None and text:
            self.unit_label = LabelBody(text, object_name="PrimaryUnitLabel")
            self.unit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            apply_primary_input_geometry(self.unit_label)
            self._layout.addWidget(self.unit_label)
        elif self.unit_label is not None:
            self.unit_label.setText(text)

        self.editor.setObjectName(
            "PrimaryNumericWithUnit" if self.unit_label is not None else "PrimaryNumeric"
        )
        style = self.editor.style()
        style.unpolish(self.editor)
        style.polish(self.editor)
        self.editor.update()

    def setSuffix(self, suffix: str) -> None:
        self.setUnit(str(suffix or "").strip())
