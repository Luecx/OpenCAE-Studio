"""Provides the shared name/target shell used by all load editors."""

from __future__ import annotations

from PyQt6.QtWidgets import QLineEdit, QMessageBox

from opencae.model.naming import is_unique
from opencae.model.selection import RegionDefinition
from opencae.ui.core.apply_dialog import ApplyDialog
from opencae.ui.core.widgets import CompactRegionSelector, ReferenceSelector
from opencae.ui.templates import (
    FieldStack,
    SectionHeading,
    apply_primary_control_height,
    dialog_buttons,
    dialog_layout,
    field_block,
    field_row,
)


class BaseLoadDialog(ApplyDialog):
    """Own common load naming, region selection and coordinate-system fields."""

    def __init__(
        self,
        title,
        project,
        regions=(),
        coordinate_systems=(),
        create_region=None,
        pick_region=None,
        show_region=True,
        show_csys=True,
        parent=None,
        default_name="",
        existing_names=(),
        entity=None,
        target_validator=None,
        target_requirement=None,
    ):
        """Build the common load header and leave a field stack for type-specific data."""
        super().__init__(parent)
        self.entity = entity
        self.existing_names = tuple(existing_names)
        self.target_validator = target_validator
        self.setWindowTitle(f"{'Edit' if entity else 'Create'} {title}")
        self.setMinimumSize(760, 520)

        self.root = dialog_layout(self)
        self.name = QLineEdit(entity.name if entity else (default_name or f"{title}-1"))
        apply_primary_control_height(self.name)
        self.root.addWidget(field_block("Name", self.name))
        self.root.addWidget(SectionHeading("Load Definition"))

        self.region = None
        common_fields = []
        if show_region:
            definition = getattr(entity, "target", RegionDefinition()) if entity else RegionDefinition()
            self.region = CompactRegionSelector(
                project,
                definition,
                regions,
                pick_region,
                create_region,
                requirement=target_requirement,
            )
            common_fields.append(field_block("Target region", self.region))

        self.csys = None
        if show_csys:
            current = (
                entity.coordinate_system_ref.entity_id
                if entity and getattr(entity, "coordinate_system_ref", None)
                else None
            )
            self.csys = ReferenceSelector((("Global", None), *coordinate_systems), current)
            common_fields.append(field_block("Coordinate system", self.csys))

        if len(common_fields) == 2:
            self.root.addWidget(field_row(*common_fields))
        elif common_fields:
            self.root.addWidget(common_fields[0])

        # Subclasses retain a concise addRow API, but the resulting fields now
        # use the same label-above hierarchy as Material/Section/Profile.
        self.form = FieldStack()
        self.root.addWidget(self.form)

    def finish(self):
        """Append standard Apply/OK controls after type-specific content is built."""
        self.root.addStretch(1)
        buttons = dialog_buttons(include_apply=True)
        self.bind_buttons(buttons, True)
        self.root.addWidget(buttons)

    def validate(self):
        """Validate naming and the unresolved target definition before commit."""
        name = self.name.text().strip()
        current = self.entity.name if self.entity else None
        if not is_unique(name, self.existing_names, current):
            QMessageBox.warning(self, "Duplicate name", f"An object named '{name}' already exists.")
            return False
        if self.region is not None:
            definition = self.region.definition()
            if definition.empty:
                QMessageBox.warning(
                    self,
                    "Missing region",
                    "Select at least one geometry, mesh, reference-point or named-region operand.",
                )
                return False
            if self.target_validator:
                error = self.target_validator(definition)
                if error:
                    QMessageBox.warning(self, "Invalid target region", error)
                    return False
        return True

    def common_values(self):
        """Return fields shared by all load entity constructors."""
        values = {"name": self.name.text().strip()}
        if self.region is not None:
            values["target"] = self.region.definition()
        if self.csys is not None:
            values["coordinate_system_id"] = self.csys.currentValue()
        return values

    def prepare_new(self, default_name, existing_names):
        """Reset common creation state after Apply creates a load."""
        self.entity = None
        self.existing_names = tuple(existing_names)
        self.name.setText(default_name)
        if self.region is not None:
            self.region.clear()
