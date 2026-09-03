"""Provides the Create/Edit Field dialog using the shared editor presentation system."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from opencae.model.core import EntityRef
from opencae.model.entities.fields import FieldDefinition
from opencae.ui.core.apply_dialog import ApplyDialog
from opencae.ui.core.file_path import FilePathEditor
from opencae.ui.core.widgets import ChevronComboBox, ReferenceSelector
from opencae.ui.templates import (
    SectionHeading,
    apply_primary_control_height,
    dialog_buttons,
    field_block,
    field_row,
)

from .field_table import FieldTable


_FIELD_LOCATIONS = (
    "Nodal",
    "Element",
    "Element-Nodal",
    "Integration Point",
    "Material Point",
    "Shell Normal",
)


class FieldDefinitionDialog(ApplyDialog):
    """Create or edit a spatial field and one of its tabular, formula, or file sources."""

    def __init__(
        self,
        field=None,
        existing_names=(),
        regions=(),
        parent=None,
        default_name="Field-1",
    ):
        """Build the field definition while preserving all existing source semantics."""
        super().__init__(parent)
        self.original = field
        self.field = field or FieldDefinition(name=default_name)
        self.existing = set(existing_names)
        self.setWindowTitle("Edit Field" if field else "Create Field")
        self.setMinimumSize(820, 620)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 18)
        root.setSpacing(16)

        self.name = QLineEdit(self.field.name)
        apply_primary_control_height(self.name)
        root.addWidget(field_block("Name", self.name))
        root.addWidget(SectionHeading("Field Definition"))

        self.location = ChevronComboBox()
        self.location.setMinimumWidth(0)
        self.location.addItems(_FIELD_LOCATIONS)
        self.location.setCurrentText(self.field.location)
        apply_primary_control_height(self.location)

        self.components = QSpinBox()
        self.components.setRange(1, 64)
        self.components.setValue(self.field.components)
        apply_primary_control_height(self.components)

        root.addWidget(
            field_row(
                field_block("Location", self.location),
                field_block("Columns", self.components),
            )
        )

        region_id = self.field.region_ref.entity_id if self.field.region_ref else None
        self.region = ReferenceSelector((("All", None), *regions), region_id)
        root.addWidget(field_block("Region", self.region))
        root.addWidget(SectionHeading("Field Source"))

        self.tabs = QTabWidget()
        self.table = FieldTable(
            self.field.components,
            self.field.table,
            location=self.field.location,
        )
        self.tabs.addTab(self.table, "Tabular")

        formula_page = QWidget()
        formula_layout = QVBoxLayout(formula_page)
        formula_layout.setContentsMargins(12, 14, 12, 12)
        self.formula = QPlainTextEdit(self.field.expression)
        self.formula.setPlaceholderText("Examples: x + y; 2*z; sqrt(x*x+y*y)")
        formula_layout.addWidget(field_block("Expression", self.formula))
        self.tabs.addTab(formula_page, "Formula")

        file_page = QWidget()
        file_layout = QVBoxLayout(file_page)
        file_layout.setContentsMargins(12, 14, 12, 12)
        file_layout.setSpacing(12)
        self.file = FilePathEditor(
            self.field.file_path,
            "Data files (*.csv *.txt *.dat);;All files (*.*)",
        )
        self.interpolation = ChevronComboBox()
        self.interpolation.setMinimumWidth(0)
        self.interpolation.addItems(("Nearest", "Linear", "Cubic"))
        self.interpolation.setCurrentText(self.field.interpolation)
        apply_primary_control_height(self.interpolation)
        file_layout.addWidget(field_block("File", self.file))
        file_layout.addWidget(field_block("Interpolation", self.interpolation))
        file_layout.addStretch(1)
        self.tabs.addTab(file_page, "File")

        root.addWidget(self.tabs, 1)
        self.components.valueChanged.connect(self.table.set_components)
        self.location.currentTextChanged.connect(self._location_changed)
        self.tabs.setCurrentIndex(
            {"Tabular": 0, "Formula": 1, "File": 2}.get(self.field.source_type, 1)
        )
        self._location_changed(self.location.currentText())

        buttons = dialog_buttons(include_apply=True)
        self.bind_buttons(buttons, True)
        root.addWidget(buttons)

    def _location_changed(self, location: str) -> None:
        """Apply domain-specific address columns and shell-normal vector semantics."""
        shell_normal = str(location) == "Shell Normal"
        if shell_normal and self.components.value() != 3:
            self.components.setValue(3)
        self.components.setEnabled(not shell_normal)
        self.table.set_domain(location, self.components.value())

    def validate(self) -> bool:
        """Reject empty or duplicate field names before committing values."""
        name = self.name.text().strip()
        duplicates = {value.casefold() for value in self.existing}
        original = self.original.name.casefold() if self.original else ""
        if not name:
            QMessageBox.warning(self, "Invalid field", "Enter a field name.")
            return False
        if name.casefold() in duplicates and name.casefold() != original:
            QMessageBox.warning(
                self,
                "Duplicate name",
                f"A field named '{name}' already exists.",
            )
            return False
        return True

    def values(self) -> dict:
        """Return constructor values for the field represented by the active source tab."""
        count = self.components.value()
        region_id = self.region.currentValue()
        location = self.location.currentText()
        return {
            "name": self.name.text().strip(),
            "location": location,
            "components": count,
            "component_names": [
                "NX", "NY", "NZ"
            ] if location == "Shell Normal" else [f"C{i + 1}" for i in range(count)],
            "region_ref": EntityRef(str(region_id), "Region") if region_id else None,
            "source_type": ("Tabular", "Formula", "File")[self.tabs.currentIndex()],
            "expression": self.formula.toPlainText().strip(),
            "table": self.table.values(),
            "file_path": self.file.text(),
            "interpolation": self.interpolation.currentText(),
            "field_type": "Vector" if location == "Shell Normal" else "Scalar" if count == 1 else "Custom",
        }

    def prepare_new(self, default_name, existing_names) -> None:
        """Reset naming state after Apply creates a field and keeps the dialog open."""
        self.original = None
        self.existing = set(existing_names)
        self.name.setText(default_name)
