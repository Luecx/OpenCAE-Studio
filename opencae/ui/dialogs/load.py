from __future__ import annotations

from PyQt6.QtWidgets import QCheckBox, QDoubleSpinBox, QGroupBox, QVBoxLayout

from opencae.ui.core.widgets import ComponentsWidget, ReferenceSelector
from .load_common import BaseLoadDialog


class LoadDialog(BaseLoadDialog):
    def __init__(self, load_type, regions=(), coordinate_systems=(), fields=(), create_region=None, parent=None, default_name="", existing_names=()):
        show_csys = load_type in {"Concentrated Load", "Surface Traction", "Volume Load"}
        show_region = load_type != "Temperature"
        super().__init__(load_type, regions, coordinate_systems, create_region, show_region, show_csys, parent, default_name, existing_names)
        self.load_type = load_type
        self.components = None; self.scalar = None; self.temperature_field = None; self.inertia = None
        if load_type == "Concentrated Load":
            self.components = ComponentsWidget(("Fx", "Fy", "Fz", "Mx", "My", "Mz"), [0.0] * 6)
            self.root.addWidget(self.components)
        elif load_type in {"Surface Traction", "Volume Load"}:
            self.components = ComponentsWidget(("Fx", "Fy", "Fz"), [0.0] * 3)
            self.root.addWidget(self.components)
        elif load_type == "Pressure":
            self.scalar = self._number(1.0); self.form.addRow("Pressure", self.scalar)
        elif load_type == "Temperature":
            self.scalar = self._number(0.0); self.form.addRow("Reference temperature", self.scalar)
            self.temperature_field = ReferenceSelector(fields, fields[0] if fields else "")
            self.form.addRow("Temperature field", self.temperature_field)
        elif load_type == "Inertia Load":
            self.inertia = [ComponentsWidget(("X", "Y", "Z"), [0.0] * 3) for _ in range(4)]
            for title, widget in zip(("Center", "Center acceleration", "Angular velocity", "Angular acceleration"), self.inertia):
                group = QGroupBox(title); group_layout = QVBoxLayout(group); group_layout.addWidget(widget); self.root.addWidget(group)
            self.point_masses = QCheckBox("Consider point masses"); self.root.addWidget(self.point_masses)
        self.finish()

    @staticmethod
    def _number(value):
        widget = QDoubleSpinBox(); widget.setDecimals(12); widget.setRange(-1e300, 1e300); widget.setValue(value); return widget

    def values(self):
        values = self.common_values()
        if self.components is not None: values["components"] = self.components.values()
        if self.load_type == "Pressure": values["pressure"] = self.scalar.value()
        if self.load_type == "Temperature":
            values.update(reference_temperature=self.scalar.value(), temperature_field=self.temperature_field.currentText())
        if self.load_type == "Inertia Load":
            keys = ("center", "center_acceleration", "angular_velocity", "angular_acceleration")
            values.update({key: tuple(widget.values()) for key, widget in zip(keys, self.inertia)})
            values["consider_point_masses"] = self.point_masses.isChecked()
        return values
