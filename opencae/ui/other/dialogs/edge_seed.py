"""Provides the modeless edge-seeding editor with deferred region selection."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from opencae.model.selection import RegionDefinition
from opencae.ui.components.controls import ControlNumericUnit
from opencae.ui.components import CompactRegionSelector
from opencae.ui.primitives.inputs import InputFormInteger, InputFormText
from opencae.ui.primitives.selects import SelectForm
from opencae.ui.primitives.labels import LabelSection
from opencae.ui.components.dialogs import apply_close_buttons
from opencae.ui.components.layouts import dialog_layout
from opencae.ui.components.form_field import FormField
from opencae.ui.components.field_row import FieldRow

class EdgeSeedDialog(QDialog):
    """Define local edge sizing by approximate size or number of divisions."""

    apply_requested = pyqtSignal(object)

    def __init__(
        self,
        project,
        options=(),
        definition=None,
        pick_callback=None,
        seed=None,
        parent=None,
        units=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Seed Edges")
        self.setModal(False)
        self.setMinimumSize(720, 480)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        root = dialog_layout(self)
        self.name = InputFormText(seed.name if seed else "Edge Seed")
        root.addWidget(FormField("Name", self.name))
        root.addWidget(LabelSection("Edge Seed Definition"))

        self.target = CompactRegionSelector(
            project,
            definition or getattr(seed, "target", RegionDefinition()),
            options,
            pick_callback,
            parent=self,
        )
        root.addWidget(FormField("Edges", self.target))

        self.method = SelectForm()
        self.method.addItems(("Size", "Number of divisions"))
        self.method.setCurrentText(seed.method if seed else "Number of divisions")

        self.size = ControlNumericUnit(
            seed.size if seed else 1.0,
            units.symbol("length") if units is not None else "",
            minimum=1e-12,
            maximum=1e30,
            decimals=9,
        )
        self.divisions = InputFormInteger(
            seed.divisions if seed and seed.divisions else 10,
            minimum=1,
            maximum=1_000_000,
        )

        self.size_field = FormField("Approximate size", self.size)
        self.divisions_field = FormField("Number of divisions", self.divisions)
        root.addWidget(
            FieldRow(
                FormField("Method", self.method),
                self.size_field,
                self.divisions_field,
            )
        )
        root.addStretch(1)

        self.method.currentTextChanged.connect(self._sync_method_fields)
        self._sync_method_fields(self.method.currentText())

        buttons = apply_close_buttons()
        apply_button = buttons.button(QDialogButtonBox.StandardButton.Apply)
        if apply_button is not None:
            apply_button.clicked.connect(lambda: self.apply_requested.emit(self.values()))
        buttons.rejected.connect(self.close)
        root.addWidget(buttons)

    def _sync_method_fields(self, method):
        use_size = str(method) == "Size"
        self.size_field.setVisible(use_size)
        self.divisions_field.setVisible(not use_size)

    def values(self):
        return {
            "name": self.name.text().strip(),
            "target": self.target.definition(),
            "method": self.method.currentText(),
            "size": self.size.value(),
            "divisions": self.divisions.value(),
        }

    def set_selected_definition(self, definition):
        self.target.set_definition(definition)

    def set_selected_edges(self, definition):
        self.set_selected_definition(definition)

    def set_divisions(self, value: int):
        self.method.setCurrentText("Number of divisions")
        self.divisions.setValue(max(1, int(value)))
