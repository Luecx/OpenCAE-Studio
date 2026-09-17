"""Provides boundary-condition editors using shared labelled-field components."""

from __future__ import annotations

from PyQt6.QtWidgets import QMessageBox

from opencae.model.naming import is_unique
from opencae.model.selection import RegionDefinition
from opencae.ui.components.apply_dialog import ApplyDialog
from opencae.ui.components import ComponentsWidget, CompactRegionSelector, ControlReferenceSelector
from opencae.ui.primitives.inputs import InputFormText
from opencae.ui.primitives.labels import LabelSection
from opencae.ui.components.layouts import dialog_layout
from opencae.ui.components.dialogs import dialog_buttons
from opencae.ui.components.form_field import FormField
from opencae.ui.components.field_row import FieldRow

class SupportDialog(ApplyDialog):
    """Create or edit a boundary condition with region, frame, and DOF components."""

    def __init__(
        self,
        support_type,
        project,
        regions=(),
        coordinate_systems=(),
        create_region=None,
        pick_region=None,
        parent=None,
        default_name="",
        existing_names=(),
        support=None,
        target_validator=None,
        target_requirement=None,
        units=None,
    ):
        """Build a boundary-condition editor while preserving target-picking behavior."""
        super().__init__(parent)
        units = units or getattr(getattr(parent, "controllers", None), "units", None)
        self.support_type = support_type
        self.support = support
        self.existing_names = tuple(existing_names)
        self.target_validator = target_validator

        self.setWindowTitle(f"{'Edit' if support else 'Create'} {support_type}")
        self.setMinimumSize(760, 500)
        root = dialog_layout(self)

        self.name = InputFormText(
            support.name if support else (default_name or f"{support_type}-1")
        )
        root.addWidget(FormField("Name", self.name))
        root.addWidget(LabelSection("Boundary Condition"))

        self.region = CompactRegionSelector(
            project,
            getattr(support, "target", RegionDefinition()),
            regions,
            pick_region,
            create_region,
            requirement=target_requirement,
        )
        csys = (
            support.coordinate_system_ref.entity_id
            if support and support.coordinate_system_ref
            else None
        )
        self.csys = ControlReferenceSelector((("Global", None), *coordinate_systems), csys)
        root.addWidget(
            FieldRow(
                FormField("Target region", self.region),
                FormField("Coordinate system", self.csys),
            )
        )

        root.addWidget(LabelSection("Components"))
        defaults = getattr(
            support,
            "components",
            ([0.0] * 6 if support_type == "Fixed" else [None] * 6),
        )
        length_unit = units.symbol("length") if units is not None else ""
        angle_unit = units.symbol("angle") if units is not None else "rad"
        self.components = ComponentsWidget(
            ("Ux", "Uy", "Uz", "Rx", "Ry", "Rz"),
            defaults,
            checkable=True,
            editable=support_type != "Fixed",
            suffixes=(
                length_unit,
                length_unit,
                length_unit,
                angle_unit,
                angle_unit,
                angle_unit,
            ),
        )
        root.addWidget(self.components)
        root.addStretch(1)

        buttons = dialog_buttons(include_apply=True)
        self.bind_buttons(buttons, True)
        root.addWidget(buttons)

    def validate(self) -> bool:
        """Validate the boundary-condition name and selected target region."""
        name = self.name.text().strip()
        if not is_unique(
            name,
            self.existing_names,
            self.support.name if self.support else None,
        ):
            QMessageBox.warning(
                self,
                "Duplicate name",
                f"A support named '{name}' already exists.",
            )
            return False
        definition = self.region.definition()
        if definition.empty:
            QMessageBox.warning(
                self,
                "Missing region",
                "Select at least one target operand.",
            )
            return False
        if self.target_validator:
            error = self.target_validator(definition)
            if error:
                QMessageBox.warning(self, "Invalid target region", error)
                return False
        return True

    def values(self) -> dict:
        """Return constructor values for the boundary condition represented by the dialog."""
        return {
            "name": self.name.text().strip(),
            "target": self.region.definition(),
            "coordinate_system_id": self.csys.currentValue(),
            "components": self.components.values(),
        }

    def prepare_new(self, default_name, existing_names) -> None:
        """Reset naming and target state after Apply creates a boundary condition."""
        self.support = None
        self.existing_names = tuple(existing_names)
        self.name.setText(default_name)
        self.region.clear()
