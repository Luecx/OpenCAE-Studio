"""Provides the Create/Edit Field dialog using the shared editor presentation system."""

from __future__ import annotations

from PyQt6.QtWidgets import QMessageBox, QTabWidget, QVBoxLayout, QWidget

from opencae.model.core import EntityRef
from opencae.model.entities.fields import (
    FieldDefinition,
    FieldInterpolation,
    FieldLocation,
    FieldSourceKind,
    FieldValueKind,
)
from opencae.ui.components.controls import ControlFilePath, ControlReferenceSelector
from opencae.ui.components.apply_dialog import ApplyDialog
from opencae.ui.primitives.inputs import InputFormInteger, InputFormMultiline, InputFormText
from opencae.ui.primitives.selects import SelectForm
from opencae.ui.primitives.labels import LabelSection
from opencae.ui.components.layouts import dialog_layout
from opencae.ui.components.dialogs import dialog_buttons
from opencae.ui.components.form_field import FormField
from opencae.ui.components.field_row import FieldRow
from .field_table import FieldTable


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
        super().__init__(parent)
        self.original = field
        self.field = field or FieldDefinition(name=default_name)
        self.existing = set(existing_names)
        self.setWindowTitle("Edit Field" if field else "Create Field")
        self.setMinimumSize(820, 620)

        root = dialog_layout(self)

        self.name = InputFormText(self.field.name)
        root.addWidget(FormField("Name", self.name))
        root.addWidget(LabelSection("Field Definition"))

        self.location = SelectForm()
        self.location.addItems([location.value for location in FieldLocation])
        self.location.setCurrentText(self.field.location)

        self.components = InputFormInteger(
            self.field.components,
            minimum=1,
            maximum=64,
        )

        root.addWidget(
            FieldRow(
                FormField("Location", self.location),
                FormField("Columns", self.components),
            )
        )

        region_id = self.field.region_ref.entity_id if self.field.region_ref else None
        self.region = ControlReferenceSelector((("All", None), *regions), region_id)
        root.addWidget(FormField("Region", self.region))
        root.addWidget(LabelSection("Field Source"))

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
        self.formula = InputFormMultiline(
            self.field.expression,
            placeholder="Examples: x + y; 2*z; sqrt(x*x+y*y)",
        )
        formula_layout.addWidget(FormField("Expression", self.formula))
        self.tabs.addTab(formula_page, "Formula")

        file_page = QWidget()
        file_layout = QVBoxLayout(file_page)
        file_layout.setContentsMargins(12, 14, 12, 12)
        file_layout.setSpacing(12)
        self.file = ControlFilePath(
            self.field.file_path,
            "Data files (*.csv *.txt *.dat);;All files (*.*)",
        )
        self.interpolation = SelectForm()
        self.interpolation.addItems(
            [interpolation.value for interpolation in FieldInterpolation]
        )
        self.interpolation.setCurrentText(self.field.interpolation)
        file_layout.addWidget(FormField("File", self.file))
        file_layout.addWidget(FormField("Interpolation", self.interpolation))
        file_layout.addStretch(1)
        self.tabs.addTab(file_page, "File")

        root.addWidget(self.tabs, 1)
        self.components.valueChanged.connect(self.table.set_components)
        self.location.currentTextChanged.connect(self._location_changed)
        self.tabs.setCurrentIndex(list(FieldSourceKind).index(self.field.source_type))
        self._location_changed(self.location.currentText())

        buttons = dialog_buttons(include_apply=True)
        self.bind_buttons(buttons, True)
        root.addWidget(buttons)

    def _location_changed(self, location: str) -> None:
        shell_normal = FieldLocation.coerce(location) is FieldLocation.SHELL_NORMAL
        if shell_normal and self.components.value() != 3:
            self.components.setValue(3)
        self.components.setEnabled(not shell_normal)
        self.table.set_domain(location, self.components.value())

    def validate(self) -> bool:
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
        count = self.components.value()
        region_id = self.region.currentValue()
        location = FieldLocation.coerce(self.location.currentText())
        return {
            "name": self.name.text().strip(),
            "location": location,
            "components": count,
            "component_names": ["NX", "NY", "NZ"]
            if location is FieldLocation.SHELL_NORMAL
            else [f"C{i + 1}" for i in range(count)],
            "region_ref": EntityRef(str(region_id), "Region") if region_id else None,
            "source_type": tuple(FieldSourceKind)[self.tabs.currentIndex()],
            "expression": self.formula.toPlainText().strip(),
            "table": self.table.values(),
            "file_path": self.file.text(),
            "interpolation": FieldInterpolation.coerce(self.interpolation.currentText()),
            "field_type": (
                FieldValueKind.VECTOR
                if location is FieldLocation.SHELL_NORMAL
                else FieldValueKind.SCALAR
                if count == 1
                else FieldValueKind.CUSTOM
            ),
        }

    def prepare_new(self, default_name, existing_names) -> None:
        self.original = None
        self.existing = set(existing_names)
        self.name.setText(default_name)
