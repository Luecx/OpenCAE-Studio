"""Provides the Unit Systems preference page and custom-system management."""

from __future__ import annotations

from copy import deepcopy

from PyQt6.QtWidgets import QHBoxLayout, QListWidget, QVBoxLayout, QWidget

from opencae.model.naming import next_name_from_names, normalized
from opencae.ui.core.widgets import ChevronComboBox
from opencae.ui.preferences.unit_system_editor import UnitSystemEditor
from opencae.ui.preferences.unit_system_table import UnitSystemTable
from opencae.ui.templates import (
    FieldLabel,
    SectionHeading,
    apply_primary_control_height,
    button,
    field_block,
)
from opencae.units import UnitSystem


class UnitSystemsPage(QWidget):
    """Manage available unit systems and select the project's current default."""

    def __init__(self, systems, selected, parent=None):
        """Build a selector column and one canonical unit-system editor/property view."""
        super().__init__(parent)
        self.systems = [deepcopy(item) for item in systems]
        self.selected_name = selected

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(20)

        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(10)
        left.addWidget(SectionHeading("Unit Systems"))
        self.list = QListWidget()
        self.list.setMinimumWidth(210)
        left.addWidget(self.list, 1)
        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(8)
        self.add = button("Add")
        self.copy = button("Duplicate")
        self.remove = button("Remove")
        for action in (self.add, self.copy, self.remove):
            actions.addWidget(action)
        left.addLayout(actions)
        root.addLayout(left, 0)

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(16)
        note = FieldLabel(
            "Length, force and time define the mechanical unit system; temperature is the fourth base unit for thermal quantities."
        )
        note.setWordWrap(True)
        right.addWidget(note)

        self.current = ChevronComboBox()
        self.current.setMinimumWidth(0)
        apply_primary_control_height(self.current)
        right.addWidget(field_block("Current unit system", self.current))

        right.addWidget(SectionHeading("Base Units"))
        self.editor = UnitSystemEditor(self._editor_changed)
        right.addWidget(self.editor)
        right.addWidget(SectionHeading("Derived Units"))
        self.table = UnitSystemTable()
        right.addWidget(self.table, 1)
        root.addLayout(right, 1)

        self.list.currentRowChanged.connect(self._load)
        self.current.currentTextChanged.connect(self._current_changed)
        self.add.clicked.connect(self._add)
        self.copy.clicked.connect(self._duplicate)
        self.remove.clicked.connect(self._remove)
        self._refresh(0)

    def _refresh(self, row=None):
        """Rebuild list/current-system choices while preserving the selected system."""
        current = self.selected_name
        self.list.blockSignals(True)
        self.list.clear()
        self.list.addItems([item.name for item in self.systems])
        self.list.blockSignals(False)
        self.current.blockSignals(True)
        self.current.clear()
        self.current.addItems([item.name for item in self.systems])
        self.current.setCurrentText(current)
        self.current.blockSignals(False)
        target_row = row if row is not None else self.list.currentRow()
        self.list.setCurrentRow(max(0, min(target_row, len(self.systems) - 1)))
        self._load(self.list.currentRow())

    def _load(self, row):
        """Load the unit system selected in the navigation list into the editor."""
        if row < 0 or not self.systems:
            return
        self.editor.load(self.systems[row])
        self._update_table()
        self.remove.setEnabled(len(self.systems) > 1)

    def _editor_changed(self):
        """Apply edits to the current in-memory unit system and refresh its labels."""
        row = self.list.currentRow()
        if row < 0:
            return
        old = self.systems[row].name
        self.editor.apply(self.systems[row])
        if self.selected_name == old:
            self.selected_name = self.systems[row].name
        self._refresh(row)

    def _current_changed(self, name):
        """Replace the current project unit-system selection."""
        if name:
            self.selected_name = name
            self._update_table()

    def _update_table(self):
        """Refresh derived-unit comparisons for edited versus selected systems."""
        row = self.list.currentRow()
        if row < 0 or not self.systems:
            return
        target = next(
            (item for item in self.systems if item.name == self.selected_name),
            self.systems[0],
        )
        self.table.refresh(self.systems[row], target)

    def _add(self):
        """Append a new custom unit system with a generated unique name."""
        name = next_name_from_names("Unit System", [item.name for item in self.systems])
        self.systems.append(UnitSystem(name))
        self._refresh(len(self.systems) - 1)

    def _duplicate(self):
        """Clone the selected unit system and assign a unique display name."""
        row = self.list.currentRow()
        if row < 0:
            return
        clone = deepcopy(self.systems[row])
        clone.name = next_name_from_names(clone.name, [item.name for item in self.systems])
        self.systems.append(clone)
        self._refresh(len(self.systems) - 1)

    def _remove(self):
        """Remove the selected custom unit system while always retaining one system."""
        row = self.list.currentRow()
        if row < 0 or len(self.systems) <= 1:
            return
        removed = self.systems.pop(row)
        if removed.name == self.selected_name:
            self.selected_name = self.systems[0].name
        self._refresh(min(row, len(self.systems) - 1))

    def validate(self):
        """Return a validation message for empty or duplicate unit-system names."""
        names = [item.name.strip() for item in self.systems]
        if any(not name for name in names):
            return "Every unit system needs a name."
        if len({normalized(name) for name in names}) != len(names):
            return "Unit-system names must be unique."
        return ""

    def values(self):
        """Return edited unit-system definitions and the selected system name."""
        return self.systems, self.selected_name
