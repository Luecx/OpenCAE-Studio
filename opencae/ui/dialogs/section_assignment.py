"""Provides the Part section-assignment editor using canonical field templates."""

from __future__ import annotations

from PyQt6.QtWidgets import QLineEdit, QMessageBox

from opencae.model.core import EntityRef
from opencae.model.naming import is_unique
from opencae.model.selection import RegionDefinition
from opencae.ui.core.apply_dialog import ApplyDialog
from opencae.ui.core.widgets import CompactRegionSelector, ReferenceSelector
from opencae.ui.templates import (
    SectionHeading,
    apply_primary_control_height,
    dialog_buttons,
    dialog_layout,
    field_block,
    field_row,
)


class SectionAssignmentDialog(ApplyDialog):
    """Assign a compatible Section and optional Orientation to a Part region."""

    def __init__(
        self,
        project,
        sections=(),
        regions=(),
        orientations=(),
        create_section=None,
        create_region=None,
        pick_region=None,
        default_name="Section Assignment-1",
        existing_names=(),
        assignment=None,
        section_filter=None,
        target_validator=None,
        target_requirement=None,
        parent=None,
    ):
        """Build the assignment selectors while preserving deferred target validation."""
        super().__init__(parent)
        self.assignment = assignment
        self.existing_names = tuple(existing_names)
        self.section_filter = section_filter
        self.target_validator = target_validator
        self.setWindowTitle("Edit Section Assignment" if assignment else "Assign Section")
        self.setMinimumSize(760, 500)

        root = dialog_layout(self)
        self.name = QLineEdit(getattr(assignment, "name", default_name))
        apply_primary_control_height(self.name)
        root.addWidget(field_block("Name", self.name))

        root.addWidget(SectionHeading("Assignment Definition"))
        current_section = assignment.section_ref.entity_id if assignment else (sections[0].id if sections else "")
        self.section = ReferenceSelector(sections, current_section, create_section)
        current_orientation = (
            assignment.orientation_ref.entity_id
            if assignment and assignment.orientation_ref
            else None
        )
        self.orientation = ReferenceSelector(
            (("Global", None), *orientations),
            current_orientation,
        )
        root.addWidget(
            field_row(
                field_block("Section", self.section),
                field_block("Orientation", self.orientation),
            )
        )

        self.target = CompactRegionSelector(
            project,
            getattr(assignment, "target", RegionDefinition()),
            regions,
            pick_region,
            create_region,
            requirement=target_requirement,
            allow_part_local=True,
        )
        root.addWidget(field_block("Target region", self.target))
        root.addStretch(1)

        buttons = dialog_buttons(include_apply=True)
        self.bind_buttons(buttons, True)
        root.addWidget(buttons)

        # Do not resolve or filter while the user is picking. The complete
        # structural compatibility check runs on Apply/OK; CAD-to-mesh
        # materialization remains a deck-generation concern.

    def _filter_sections(self, definition):
        """Refresh section candidates when a controller explicitly requests filtering."""
        if self.section_filter:
            self.section.set_values(tuple(self.section_filter(definition)))

    def values(self):
        """Return persistent references plus the unresolved target definition."""
        section_id = self.section.currentValue()
        orientation_id = self.orientation.currentValue()
        return {
            "name": self.name.text().strip(),
            "section_ref": (
                EntityRef(str(section_id), "Section")
                if section_id
                else EntityRef(expected_type="Section")
            ),
            "target": self.target.definition(),
            "orientation_ref": (
                EntityRef(str(orientation_id), "Orientation")
                if orientation_id
                else None
            ),
        }

    def validate(self):
        """Validate naming, selected section and target compatibility before commit."""
        current_name = self.assignment.name if self.assignment else None
        if not is_unique(self.name.text().strip(), self.existing_names, current_name):
            QMessageBox.warning(
                self,
                "Duplicate name",
                f"A section assignment named '{self.name.text().strip()}' already exists.",
            )
            return False
        if not self.section.currentValue():
            QMessageBox.warning(self, "Missing section", "Create or select a section.")
            return False
        definition = self.target.definition()
        if definition.empty:
            QMessageBox.warning(self, "Missing region", "Select at least one target operand.")
            return False
        if self.target_validator:
            error = self.target_validator(definition)
            if error:
                QMessageBox.warning(self, "Invalid target region", error)
                return False
        if self.section_filter and self.section.currentValue() not in {
            item.id for item in self.section_filter(definition)
        }:
            QMessageBox.warning(
                self,
                "Incompatible section",
                "The selected section is not compatible with the directly selected mesh element families.",
            )
            return False
        return True
