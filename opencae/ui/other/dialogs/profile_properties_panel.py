"""Displays derived profile section properties in reusable read-only fields."""

from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from opencae.ui.components.controls import ControlReadOnlyValue
from opencae.ui.primitives.labels import LabelSection
from opencae.ui.components.form_field import FormField
from opencae.ui.components.field_row import FieldRow

_PROPERTY_LAYOUT = (
    ("Area", "Area", "area"),
    ("Centroid y", "Centroid y", "length"),
    ("Centroid z", "Centroid z", "length"),
    ("Iyy", "Iyy", "section_inertia"),
    ("Izz", "Izz", "section_inertia"),
    ("Iyz", "Iyz", "section_inertia"),
    ("Torsion constant", "It", "section_inertia"),
)


class ProfilePropertiesPanel(QWidget):
    """Present derived profile properties without editable widget semantics."""

    def __init__(self, units=None, parent=None):
        """Build the fixed Area/Centroid/Inertia property hierarchy."""
        super().__init__(parent)
        self.units = units
        self._values: dict[str, ControlReadOnlyValue] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(LabelSection("Profile Properties"))

        fields = {}
        for key, label, quantity in _PROPERTY_LAYOUT:
            unit = self.units.symbol(quantity) if self.units is not None else ""
            value = ControlReadOnlyValue("0", unit)
            self._values[key] = value
            fields[key] = FormField(label, value)

        layout.addWidget(fields["Area"])
        layout.addWidget(FieldRow(fields["Centroid y"], fields["Centroid z"]))
        layout.addWidget(FieldRow(fields["Iyy"], fields["Izz"]))
        layout.addWidget(FieldRow(fields["Iyz"], fields["Torsion constant"]))
        layout.addStretch(1)

    def set_properties(self, values: dict[str, float]) -> None:
        """Refresh the displayed derived values after profile dimensions change."""
        for key, widget in self._values.items():
            value = float(values.get(key, 0.0))
            widget.set_value(f"{value:.8g}")
