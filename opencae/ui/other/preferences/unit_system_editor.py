"""Provides the base-unit editor used by the Unit Systems preference page."""

from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from opencae.ui.primitives.inputs import InputFormText
from opencae.ui.primitives.selects import SelectForm
from opencae.ui.components.form_field import FormField
from opencae.ui.components.field_row import FieldRow
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

        self.name = InputFormText()
        root.addWidget(FormField("Name", self.name))

        self.combos = {}
        first_row = []
        second_row = []
        for key, label in (
            ("length", "Length"),
            ("force", "Force"),
            ("time", "Time"),
            ("temperature", "Temperature"),
        ):
            combo = SelectForm()
            combo.addItems(tuple(BASE_CATALOGS[key]))
            self.combos[key] = combo
            (first_row if len(first_row) < 2 else second_row).append(FormField(label, combo))
        root.addWidget(FieldRow(*first_row))
        root.addWidget(FieldRow(*second_row))

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
