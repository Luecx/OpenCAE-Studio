"""Provides Create/Edit Profile dialogs with canonical control geometry."""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QLineEdit, QMessageBox, QTableWidgetItem, QWidget

from opencae.model.entities.profiles.calculations import profile_parameters, profile_properties
from opencae.ui.core.apply_dialog import ApplyDialog
from opencae.ui.core.widgets import ChevronComboBox
from opencae.ui.templates import (
    NumericUnitInput,
    apply_primary_control_height,
    dialog_buttons,
    form_layout,
    read_only_table,
    scaffold_dialog,
)
from .profile_graph_editor import GraphProfileEditor


PROFILE_TYPES = (
    "Rectangle",
    "Box",
    "Pipe",
    "Circle",
    "I-profile",
    "H-profile",
    "C-profile",
    "U-profile",
    "General",
    "Graph profile",
)

_PROPERTY_QUANTITIES = {
    "Area": "area",
    "Centroid y": "length",
    "Centroid z": "length",
    "Iyy": "section_inertia",
    "Izz": "section_inertia",
    "Iyz": "section_inertia",
    "Torsion constant": "section_inertia",
}


class ProfileDialog(ApplyDialog):
    """Create or edit all profile types using one consistent control metric."""

    def __init__(
        self,
        profile=None,
        existing_names=(),
        parent=None,
        initial_type=None,
        default_name="Profile-1",
        units=None,
    ):
        super().__init__(parent)
        self.profile = profile
        self.units = units
        self.existing_names = {name.casefold() for name in existing_names}
        self._editors = {}

        title = "Edit Profile" if profile else "Create Profile"
        scaffold = scaffold_dialog(self, title, width=880)
        self.setMinimumHeight(520)

        self.name = QLineEdit(profile.name if profile else default_name)
        apply_primary_control_height(self.name)

        self.kind = ChevronComboBox()
        self.kind.addItems(PROFILE_TYPES)
        self.kind.setCurrentText(profile.profile_type if profile else (initial_type or "Box"))
        apply_primary_control_height(self.kind)

        scaffold.form.addRow("Name", self.name)
        scaffold.form.addRow("Profile type", self.kind)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(16)

        self.form_host = QWidget()
        self.form = form_layout(self.form_host)
        body.addWidget(self.form_host, 1)

        self.properties = read_only_table(
            ("Property", "Value", "Unit"),
            stretch_columns=(0, 1),
        )
        body.addWidget(self.properties, 1)
        scaffold.root.addLayout(body, 1)

        buttons = dialog_buttons(include_apply=True)
        self.bind_buttons(buttons, True)
        scaffold.root.addWidget(buttons)

        self.kind.currentTextChanged.connect(self._rebuild)
        self._rebuild()

    def _symbol(self, quantity):
        """Return the current project symbol for a physical quantity."""
        return self.units.symbol(quantity) if self.units is not None else ""

    def _rebuild(self):
        """Rebuild the parameter editor for the selected profile type."""
        while self.form.rowCount():
            self.form.removeRow(0)
        self._editors = {}

        current = (
            self.profile.dimensions
            if self.profile and self.kind.currentText() == self.profile.profile_type
            else {}
        )
        if self.kind.currentText() == "Graph profile":
            editor = GraphProfileEditor(
                current.get("nodes", "1,-20,0\n2,20,0"),
                current.get("segments", "1,2,2.0"),
            )
            editor.connect_changed(self._update_properties)
            self._editors["graph"] = editor
            self.form.addRow(editor)
        else:
            unit = self._symbol("length")
            for key, text, default in profile_parameters(self.kind.currentText()):
                # Profile dimensions use the same segmented numeric control as
                # Materials, so adding or removing a unit never changes height.
                editor = NumericUnitInput(
                    value=float(current.get(key, default)),
                    unit=unit,
                    minimum=-1e30,
                    maximum=1e30,
                    decimals=6,
                )
                editor.valueChanged.connect(self._update_properties)
                self._editors[key] = editor
                self.form.addRow(text, editor)
        self._update_properties()

    def _dimensions(self):
        """Return dimensions in the representation expected by profile models."""
        if "graph" in self._editors:
            return self._editors["graph"].values()
        return {key: editor.value() for key, editor in self._editors.items()}

    def _update_properties(self, *_args):
        """Recalculate and display the derived geometric profile properties."""
        data = profile_properties(self.kind.currentText(), self._dimensions())
        self.properties.setRowCount(len(data))
        for row, (name, value) in enumerate(data.items()):
            quantity = _PROPERTY_QUANTITIES.get(name)
            unit = self._symbol(quantity) if quantity else ""
            self.properties.setItem(row, 0, QTableWidgetItem(name))
            self.properties.setItem(row, 1, QTableWidgetItem(f"{value:.8g}"))
            self.properties.setItem(row, 2, QTableWidgetItem(unit))

    def validate(self):
        """Reject empty or duplicate profile names before committing."""
        name = self.name.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid profile", "Enter a profile name.")
            return False
        duplicate = name.casefold() in self.existing_names
        unchanged = self.profile is not None and name.casefold() == self.profile.name.casefold()
        if duplicate and not unchanged:
            QMessageBox.warning(
                self,
                "Duplicate name",
                f"A profile named '{name}' already exists.",
            )
            return False
        return True

    def values(self):
        """Return values consumed by the profile factory."""
        return {
            "name": self.name.text().strip(),
            "profile_type": self.kind.currentText(),
            "dimensions": self._dimensions(),
        }

    def prepare_new(self, default_name, existing_names):
        """Reset name state when Apply keeps a create dialog open."""
        self.profile = None
        self.existing_names = {name.casefold() for name in existing_names}
        self.name.setText(default_name)
