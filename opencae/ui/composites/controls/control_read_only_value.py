"""Read-only value control with an optional fixed unit segment."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QWidget

from opencae.ui.primitives.inputs.geometry import apply_primary_input_geometry
from opencae.ui.primitives.labels import LabelBody


class ControlReadOnlyValue(QWidget):
    def __init__(self, value: str = "", unit: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("ReadOnlyValue")
        apply_primary_input_geometry(self)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.value_label = LabelBody(
            str(value),
            object_name="ReadOnlyValueTextWithUnit" if unit else "ReadOnlyValueText",
        )
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        apply_primary_input_geometry(self.value_label)
        layout.addWidget(self.value_label, 1)
        self.unit_label = None
        if unit:
            self.unit_label = LabelBody(str(unit), object_name="ReadOnlyValueUnit")
            self.unit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            apply_primary_input_geometry(self.unit_label)
            layout.addWidget(self.unit_label)

    def set_value(self, value: str, unit: str | None = None) -> None:
        self.value_label.setText(str(value))
        if unit is not None and self.unit_label is not None:
            self.unit_label.setText(str(unit))
