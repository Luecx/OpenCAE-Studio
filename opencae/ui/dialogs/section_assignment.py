from PyQt6.QtWidgets import QMessageBox

from opencae.model.naming import is_unique
from opencae.ui.core.fields import FieldSpec
from opencae.ui.core.form_dialog import FormDialog


class SectionAssignmentDialog(FormDialog):
    def __init__(
        self,
        sections=(),
        regions=(),
        orientations=(),
        create_section=None,
        create_region=None,
        default_name="Section Assignment-1",
        existing_names=(),
        assignment=None,
        parent=None,
    ):
        self.assignment = assignment
        self.existing_names = tuple(existing_names)
        super().__init__(
            "Edit Section Assignment" if assignment else "Assign Section",
            (
                FieldSpec("name", "Name", "text", getattr(assignment, "name", default_name)),
                FieldSpec(
                    "section_name",
                    "Section",
                    "reference",
                    getattr(assignment, "section_name", sections[0] if sections else ""),
                    tuple(sections),
                    create_callback=create_section,
                ),
                FieldSpec(
                    "region_name",
                    "Region",
                    "reference",
                    getattr(assignment, "region_name", regions[0] if regions else ""),
                    tuple(regions),
                    create_callback=create_region,
                ),
                FieldSpec(
                    "orientation_name",
                    "Orientation",
                    "choice",
                    getattr(assignment, "orientation_name", "Global"),
                    tuple(["Global", *orientations]),
                ),
            ),
            parent,
            width=560,
        )

    def accept(self):
        values = self.values()
        current_name = self.assignment.name if self.assignment else None
        if not is_unique(values["name"], self.existing_names, current_name):
            QMessageBox.warning(self, "Duplicate name", f"A section assignment named '{values['name']}' already exists.")
            return
        if not values["section_name"]:
            QMessageBox.warning(self, "Missing section", "Create or select a section.")
            return
        if not values["region_name"]:
            QMessageBox.warning(self, "Missing region", "Create or select a region.")
            return
        super().accept()
