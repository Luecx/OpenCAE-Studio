"""Provides type-specific load editors on top of the shared load dialog shell."""

from __future__ import annotations

from PyQt6.QtWidgets import QCheckBox

from opencae.ui.core.widgets import ChevronComboBox, ComponentsWidget, ReferenceSelector
from opencae.ui.templates import (
    NumericUnitInput,
    SectionHeading,
    apply_primary_control_height,
    field_block,
    field_row,
)

from .load_common import BaseLoadDialog


class LoadDialog(BaseLoadDialog):
    """Create or edit one load type while sharing target and naming behavior."""

    def __init__(
        self,
        load_type,
        project,
        regions=(),
        coordinate_systems=(),
        fields=(),
        create_region=None,
        pick_region=None,
        parent=None,
        default_name="",
        existing_names=(),
        load=None,
        target_validator=None,
        target_requirement=None,
        units=None,
    ):
        """Build the fields required by the selected load type."""
        units = units or getattr(getattr(parent, "controllers", None), "units", None)
        show_csys = load_type in {"Concentrated Load", "Surface Traction", "Volume Load"}
        show_region = load_type != "Temperature"
        super().__init__(
            load_type,
            project,
            regions,
            coordinate_systems,
            create_region,
            pick_region,
            show_region,
            show_csys,
            parent,
            default_name,
            existing_names,
            load,
            target_validator,
            target_requirement,
        )
        self.load_type = load_type
        self.components = None
        self.scalar = None
        self.temperature_field = None
        self.inertia = None
        self.distribution = None

        symbol = lambda quantity: units.symbol(quantity) if units is not None else ""

        if load_type == "Concentrated Load":
            self.distribution = ChevronComboBox()
            self.distribution.setMinimumWidth(0)
            self.distribution.addItem("Value per resolved node", "per_node")
            self.distribution.addItem("Total value, uniformly distributed", "total_uniform")
            index = self.distribution.findData(str(getattr(load, "distribution", "per_node")))
            self.distribution.setCurrentIndex(max(0, index))
            apply_primary_control_height(self.distribution)
            self.form.addRow("Interpretation", self.distribution)

            self.root.addWidget(SectionHeading("Load Components"))
            self.components = ComponentsWidget(
                ("Fx", "Fy", "Fz", "Mx", "My", "Mz"),
                getattr(load, "components", [0.0] * 6),
                suffixes=(symbol("force"),) * 3 + (symbol("moment"),) * 3,
            )
            self.root.addWidget(self.components)

        elif load_type == "Surface Traction":
            self.root.addWidget(SectionHeading("Load Components"))
            self.components = ComponentsWidget(
                ("Fx", "Fy", "Fz"),
                getattr(load, "components", [0.0] * 3),
                suffixes=symbol("pressure"),
            )
            self.root.addWidget(self.components)

        elif load_type == "Volume Load":
            self.root.addWidget(SectionHeading("Load Components"))
            self.components = ComponentsWidget(
                ("Fx", "Fy", "Fz"),
                getattr(load, "components", [0.0] * 3),
                suffixes=symbol("volume_load"),
            )
            self.root.addWidget(self.components)

        elif load_type == "Pressure":
            self.scalar = self._number(
                getattr(load, "pressure", 1.0),
                symbol("pressure"),
            )
            self.form.addRow("Pressure", self.scalar)

        elif load_type == "Temperature":
            self.scalar = self._number(
                getattr(load, "reference_temperature", 0.0),
                symbol("temperature"),
            )
            current = (
                load.temperature_field_ref.entity_id
                if load and getattr(load, "temperature_field_ref", None)
                else (fields[0].id if fields else "")
            )
            self.temperature_field = ReferenceSelector(fields, current)
            self.form.addRow("Reference temperature", self.scalar)
            self.form.addRow("Temperature field", self.temperature_field)

        elif load_type == "Inertia Load":
            values = (
                getattr(load, "center", (0, 0, 0)),
                getattr(load, "center_acceleration", (0, 0, 0)),
                getattr(load, "angular_velocity", (0, 0, 0)),
                getattr(load, "angular_acceleration", (0, 0, 0)),
            )
            quantities = ("length", "acceleration", "frequency", "angular_acceleration")
            self.inertia = [
                ComponentsWidget(("X", "Y", "Z"), value, suffixes=symbol(quantity))
                for value, quantity in zip(values, quantities)
            ]
            self.root.addWidget(SectionHeading("Inertia Definition"))
            self.root.addWidget(
                field_row(
                    field_block("Center", self.inertia[0]),
                    field_block("Center acceleration", self.inertia[1]),
                )
            )
            self.root.addWidget(
                field_row(
                    field_block("Angular velocity", self.inertia[2]),
                    field_block("Angular acceleration", self.inertia[3]),
                )
            )
            self.point_masses = QCheckBox("Consider point masses")
            self.point_masses.setChecked(bool(getattr(load, "consider_point_masses", False)))
            self.root.addWidget(self.point_masses)

        self.finish()

    @staticmethod
    def _number(value, unit=""):
        """Return the canonical scalar editor used by single-value loads."""
        return NumericUnitInput(
            value,
            unit,
            minimum=-1e300,
            maximum=1e300,
            decimals=12,
        )

    def values(self):
        """Return constructor values for the active load type."""
        values = self.common_values()
        if self.components is not None:
            values["components"] = self.components.values()
        if self.distribution is not None:
            values["distribution"] = self.distribution.currentData()
        if self.load_type == "Pressure":
            values["pressure"] = self.scalar.value()
        if self.load_type == "Temperature":
            values.update(
                reference_temperature=self.scalar.value(),
                temperature_field_id=self.temperature_field.currentValue(),
            )
        if self.load_type == "Inertia Load":
            keys = ("center", "center_acceleration", "angular_velocity", "angular_acceleration")
            values.update(
                {
                    key: tuple(widget.values())
                    for key, widget in zip(keys, self.inertia)
                }
            )
            values["consider_point_masses"] = self.point_masses.isChecked()
        return values
