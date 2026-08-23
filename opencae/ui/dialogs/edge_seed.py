"""Provides the modeless edge-seeding editor with deferred region selection."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLineEdit, QSpinBox

from opencae.model.selection import RegionDefinition
from opencae.ui.core.widgets import ChevronComboBox, CompactRegionSelector
from opencae.ui.templates import (
    NumericUnitInput,
    SectionHeading,
    apply_close_buttons,
    apply_primary_control_height,
    dialog_layout,
    field_block,
    field_row,
)


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
        """Build the edge target and mutually exclusive seeding parameters."""
        super().__init__(parent)
        self.setWindowTitle("Seed Edges")
        self.setModal(False)
        self.setMinimumSize(720, 480)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        root = dialog_layout(self)
        self.name = QLineEdit(seed.name if seed else "Edge Seed")
        apply_primary_control_height(self.name)
        root.addWidget(field_block("Name", self.name))
        root.addWidget(SectionHeading("Edge Seed Definition"))

        self.target = CompactRegionSelector(
            project,
            definition or getattr(seed, "target", RegionDefinition()),
            options,
            pick_callback,
            parent=self,
        )
        root.addWidget(field_block("Edges", self.target))

        self.method = ChevronComboBox()
        self.method.setMinimumWidth(0)
        self.method.addItems(("Size", "Number of divisions"))
        self.method.setCurrentText(seed.method if seed else "Number of divisions")
        apply_primary_control_height(self.method)

        self.size = NumericUnitInput(
            seed.size if seed else 1.0,
            units.symbol("length") if units is not None else "",
            minimum=1e-12,
            maximum=1e30,
            decimals=9,
        )
        self.divisions = QSpinBox()
        self.divisions.setRange(1, 1_000_000)
        self.divisions.setValue(seed.divisions if seed and seed.divisions else 10)
        self.divisions.setMinimumWidth(0)
        apply_primary_control_height(self.divisions)

        self.size_field = field_block("Approximate size", self.size)
        self.divisions_field = field_block("Number of divisions", self.divisions)
        root.addWidget(
            field_row(
                field_block("Method", self.method),
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
        """Show only the scalar parameter relevant to the selected seed method."""
        use_size = str(method) == "Size"
        self.size_field.setVisible(use_size)
        self.divisions_field.setVisible(not use_size)

    def values(self):
        """Return the current unresolved edge definition and seed parameters."""
        return {
            "name": self.name.text().strip(),
            "target": self.target.definition(),
            "method": self.method.currentText(),
            "size": self.size.value(),
            "divisions": self.divisions.value(),
        }

    def set_selected_definition(self, definition):
        """Replace the current edge target from an external selection source."""
        self.target.set_definition(definition)

    def set_selected_edges(self, definition):
        """Compatibility alias for replacing the edge target definition."""
        self.set_selected_definition(definition)

    def set_divisions(self, value: int):
        """Switch to division-count mode and set its integer value."""
        self.method.setCurrentText("Number of divisions")
        self.divisions.setValue(max(1, int(value)))
