"""Provides Create/Edit Profile with the shared label-above-control styling."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from opencae.model.entities.profiles.calculations import (
    profile_parameters,
    profile_properties,
)
from opencae.ui.core.apply_dialog import ApplyDialog
from opencae.ui.core.widgets import ChevronComboBox
from opencae.ui.templates import (
    NumericUnitInput,
    apply_primary_control_height,
    dialog_buttons,
    field_block,
    read_only_table,
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
    """Create or edit a section profile using vertically labelled controls."""

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

        self.setWindowTitle("Edit Profile" if profile else "Create Profile")
        self.setMinimumSize(880, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 18)
        root.setSpacing(16)

        self.name = QLineEdit(profile.name if profile else default_name)
        apply_primary_control_height(self.name)
        root.addWidget(field_block("Name", self.name))

        self.kind = ChevronComboBox()
        self.kind.setMinimumWidth(0)
        apply_primary_control_height(self.kind)
        self.kind.addItems(PROFILE_TYPES)
        self.kind.setCurrentText(
            profile.profile_type if profile else (initial_type or "Box")
        )
        root.addWidget(field_block("Profile type", self.kind))

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(16)

        self.parameter_host = QWidget()
        self.parameter_layout = QVBoxLayout(self.parameter_host)
        self.parameter_layout.setContentsMargins(0, 0, 0, 0)
        self.parameter_layout.setSpacing(12)
        body.addWidget(self.parameter_host, 1)

        self.properties = read_only_table(
            ("Property", "Value", "Unit"),
            stretch_columns=(0, 1),
        )
        body.addWidget(self.properties, 1)
        root.addLayout(body, 1)

        buttons = dialog_buttons(include_apply=True)
        self.bind_buttons(buttons, True)
        root.addWidget(buttons)

        self.kind.currentTextChanged.connect(self._rebuild)
        self._rebuild()

    def _symbol(self, quantity: str | None) -> str:
        """Return the active project symbol for one physical quantity."""
        return self.units.symbol(quantity) if quantity and self.units is not None else ""

    def _clear_parameters(self) -> None:
        """Remove controls belonging to the previously selected profile type."""
        while self.parameter_layout.count():
            item = self.parameter_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _rebuild(self, *_args) -> None:
        """Rebuild profile-specific inputs below the profile-type selector."""
        self._clear_parameters()
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
            self.parameter_layout.addWidget(editor)
        else:
            unit = self._symbol("length")
            for key, text, default in profile_parameters(self.kind.currentText()):
                editor = NumericUnitInput(
                    float(current.get(key, default)),
                    unit,
                    decimals=6,
                )
                editor.valueChanged.connect(self._update_properties)
                self._editors[key] = editor
                self.parameter_layout.addWidget(field_block(text, editor))

        self.parameter_layout.addStretch(1)
        self._update_properties()

    def _dimensions(self):
        """Return the active profile dimension payload."""
        if "graph" in self._editors:
            return self._editors["graph"].values()
        return {key: editor.value() for key, editor in self._editors.items()}

    def _update_properties(self, *_args) -> None:
        """Recompute read-only section properties after an input change."""
        data = profile_properties(self.kind.currentText(), self._dimensions())
        self.properties.setRowCount(len(data))
        for row, (name, value) in enumerate(data.items()):
            quantity = _PROPERTY_QUANTITIES.get(name)
            unit = self._symbol(quantity)
            self.properties.setItem(row, 0, QTableWidgetItem(name))
            self.properties.setItem(row, 1, QTableWidgetItem(f"{value:.8g}"))
            self.properties.setItem(row, 2, QTableWidgetItem(unit))

    def validate(self) -> bool:
        """Reject empty and duplicate profile names before committing."""
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

    def values(self) -> dict:
        """Return constructor values for the current profile."""
        return {
            "name": self.name.text().strip(),
            "profile_type": self.kind.currentText(),
            "dimensions": self._dimensions(),
        }

    def prepare_new(self, default_name, existing_names) -> None:
        """Reset the reusable dialog after Apply creates a profile."""
        self.profile = None
        self.existing_names = {name.casefold() for name in existing_names}
        self.name.setText(default_name)
