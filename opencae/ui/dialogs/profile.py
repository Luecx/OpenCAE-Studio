"""Provides Create/Edit Profile with shared editor and property-panel templates."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QScrollArea,
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
    SectionHeading,
    VerticalSeparator,
    apply_primary_control_height,
    dialog_buttons,
    field_block,
)

from .profile_graph_editor import GraphProfileEditor
from .profile_preview_widget import ProfilePreviewWidget
from .profile_properties_panel import ProfilePropertiesPanel


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


class ProfileDialog(ApplyDialog):
    """Create or edit a profile with definition and derived-property columns."""

    def __init__(
        self,
        profile=None,
        existing_names=(),
        parent=None,
        initial_type=None,
        default_name="Profile-1",
        units=None,
    ):
        """Build the profile editor using the canonical resource-dialog styling."""
        super().__init__(parent)
        self.profile = profile
        self.units = units
        self.existing_names = {name.casefold() for name in existing_names}
        self._editors = {}

        self.setWindowTitle("Edit Profile" if profile else "Create Profile")
        self.setMinimumSize(920, 560)

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
        body.setSpacing(18)

        definition_panel = QWidget()
        definition_layout = QVBoxLayout(definition_panel)
        definition_layout.setContentsMargins(0, 0, 0, 0)
        definition_layout.setSpacing(12)
        definition_layout.addWidget(SectionHeading("Profile Definition"))

        self.preview = ProfilePreviewWidget(self.kind.currentText())
        definition_layout.addWidget(self.preview)

        self.parameter_host = QWidget()
        self.parameter_layout = QVBoxLayout(self.parameter_host)
        self.parameter_layout.setContentsMargins(0, 0, 0, 0)
        self.parameter_layout.setSpacing(12)

        parameter_scroll = QScrollArea()
        parameter_scroll.setObjectName("ProfileParametersScroll")
        parameter_scroll.setWidgetResizable(True)
        parameter_scroll.setFrameShape(QFrame.Shape.NoFrame)
        parameter_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        parameter_scroll.viewport().setObjectName("ProfileParametersViewport")
        self.parameter_host.setObjectName("ProfileParametersContent")
        # These three surfaces are structural only, so the dialog background
        # must remain continuous around the actual editor controls.
        parameter_scroll.setStyleSheet(
            "QScrollArea#ProfileParametersScroll, "
            "QWidget#ProfileParametersViewport, "
            "QWidget#ProfileParametersContent {"
            "background: transparent; border: none;"
            "}"
        )
        parameter_scroll.setWidget(self.parameter_host)
        definition_layout.addWidget(parameter_scroll, 1)
        body.addWidget(definition_panel, 1)

        # The divider communicates that the left side owns editable dimensions
        # while the right side only reports values derived from those inputs.
        body.addWidget(VerticalSeparator())

        self.properties = ProfilePropertiesPanel(self.units)
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
            editor.connect_changed(self._refresh_profile_state)
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
                editor.valueChanged.connect(self._refresh_profile_state)
                self._editors[key] = editor
                self.parameter_layout.addWidget(field_block(text, editor))

        self.parameter_layout.addStretch(1)
        self._refresh_profile_state()

    def _dimensions(self) -> dict:
        """Return the active profile dimension payload."""
        if "graph" in self._editors:
            return self._editors["graph"].values()
        return {key: editor.value() for key, editor in self._editors.items()}

    def _refresh_profile_state(self, *_args) -> None:
        """Refresh derived properties and preview from one dimension snapshot."""
        dimensions = self._dimensions()
        profile_type = self.kind.currentText()
        data = profile_properties(profile_type, dimensions)
        self.properties.set_properties(data)
        self.preview.set_profile_state(profile_type, dimensions)

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
