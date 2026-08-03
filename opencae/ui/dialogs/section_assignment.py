from PyQt6.QtWidgets import QFormLayout, QLineEdit, QMessageBox, QVBoxLayout

from opencae.model.core import EntityRef
from opencae.model.naming import is_unique
from opencae.model.selection import RegionDefinition
from opencae.ui.core.apply_dialog import ApplyDialog
from opencae.ui.core.controls import dialog_buttons
from opencae.ui.core.widgets import ReferenceSelector, CompactRegionSelector


class SectionAssignmentDialog(ApplyDialog):
    def __init__(self, project, sections=(), regions=(), orientations=(), create_section=None, create_region=None,
                 pick_region=None, default_name="Section Assignment-1", existing_names=(), assignment=None,
                 section_filter=None, target_validator=None, target_requirement=None, parent=None):
        super().__init__(parent)
        self.assignment = assignment; self.existing_names = tuple(existing_names); self.section_filter = section_filter; self.target_validator = target_validator
        self.setWindowTitle("Edit Section Assignment" if assignment else "Assign Section"); self.setMinimumWidth(720)
        root = QVBoxLayout(self); form = QFormLayout()
        self.name = QLineEdit(getattr(assignment, "name", default_name))
        current_section = assignment.section_ref.entity_id if assignment else (sections[0].id if sections else "")
        self.section = ReferenceSelector(sections, current_section, create_section)
        self.target = CompactRegionSelector(project, getattr(assignment, "target", RegionDefinition()), regions, pick_region, create_region, requirement=target_requirement, allow_part_local=True)
        current_orientation = assignment.orientation_ref.entity_id if assignment and assignment.orientation_ref else None
        self.orientation = ReferenceSelector((("Global", None), *orientations), current_orientation)
        form.addRow("Name", self.name); form.addRow("Section", self.section); form.addRow("Target region", self.target); form.addRow("Orientation", self.orientation)
        root.addLayout(form); buttons = dialog_buttons(include_apply=True); self.bind_buttons(buttons, True); root.addWidget(buttons)
        # Do not resolve or filter while the user is picking.  The complete
        # structural compatibility check runs once on Apply/OK; actual CAD-to-mesh
        # materialization remains a deck-generation concern.

    def _filter_sections(self, definition):
        if self.section_filter: self.section.set_values(tuple(self.section_filter(definition)))

    def values(self):
        section_id = self.section.currentValue(); orientation_id = self.orientation.currentValue()
        return {
            "name": self.name.text().strip(),
            "section_ref": EntityRef(str(section_id), "Section") if section_id else EntityRef(expected_type="Section"),
            "target": self.target.definition(),
            "orientation_ref": EntityRef(str(orientation_id), "Orientation") if orientation_id else None,
        }

    def validate(self):
        current_name = self.assignment.name if self.assignment else None
        if not is_unique(self.name.text().strip(), self.existing_names, current_name):
            QMessageBox.warning(self, "Duplicate name", f"A section assignment named '{self.name.text().strip()}' already exists."); return False
        if not self.section.currentValue(): QMessageBox.warning(self, "Missing section", "Create or select a section."); return False
        definition = self.target.definition()
        if definition.empty: QMessageBox.warning(self, "Missing region", "Select at least one target operand."); return False
        if self.target_validator:
            error = self.target_validator(definition)
            if error: QMessageBox.warning(self, "Invalid target region", error); return False
        if self.section_filter and self.section.currentValue() not in {item.id for item in self.section_filter(definition)}:
            QMessageBox.warning(self, "Incompatible section", "The selected section is not compatible with the directly selected mesh element families."); return False
        return True
