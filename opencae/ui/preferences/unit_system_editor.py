"""Provides the base-unit editor used by the Unit Systems preference page."""

from __future__ import annotations

from PyQt6.QtWidgets import QLineEdit, QVBoxLayout, QWidget

from opencae.ui.core.widgets import ChevronComboBox
from opencae.ui.templates import apply_primary_control_height, field_block, field_row
from opencae.units.catalog import BASE_CATALOGS


class UnitSystemEditor(QWidget):
    """Edit one unit-system name and its four independent base units."""

    def __init__(self, changed, parent=None):
        """Build name and base-unit controls with equal-width canonical fields."""
        super().__init__(parent)
        self.changed = changed
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        self.name = QLineEdit()
        apply_primary_control_height(self.name)
        root.addWidget(field_block("Name", self.name))

        self.combos = {}
        first_row = []
        second_row = []
        for key, label in (
            ("length", "Length"),
            ("force", "Force"),
            ("time", "Time"),
            ("temperature", "Temperature"),
        ):
            combo = ChevronComboBox()
            combo.setMinimumWidth(0)
            combo.addItems(tuple(BASE_CATALOGS[key]))
            apply_primary_control_height(combo)
            self.combos[key] = combo
            (first_row if len(first_row) < 2 else second_row).append(field_block(label, combo))
        root.addWidget(field_row(*first_row))
        root.addWidget(field_row(*second_row))

        self.name.editingFinished.connect(changed)
        for combo in self.combos.values():
            combo.currentTextChanged.connect(lambda _text, callback=changed: callback())

    def load(self, system):
        """Populate the editor from one UnitSystem without emitting change callbacks."""
        self.name.blockSignals(True)
        self.name.setText(system.name)
        self.name.blockSignals(False)
        for key, combo in self.combos.items():
            combo.blockSignals(True)
            combo.setCurrentText(getattr(system, key))
            combo.blockSignals(False)

    def apply(self, system):
        """Write the current base-unit selections back to one UnitSystem instance."""
        system.name = self.name.text().strip()
        for key, combo in self.combos.items():
            setattr(system, key, combo.currentText())
