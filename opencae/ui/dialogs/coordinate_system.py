"""Provides the modeless coordinate-system editor and viewport-pick integration."""

from __future__ import annotations

import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLineEdit, QMessageBox

from opencae.model.naming import is_unique
from opencae.ui.core.widgets import ChevronComboBox, XYZPicker
from opencae.ui.templates import (
    SectionHeading,
    apply_primary_control_height,
    dialog_buttons,
    dialog_layout,
    field_block,
    field_row,
)

_POINT_KINDS = ("geometry_vertex", "datum_point", "reference_point")
_DIRECTION_KINDS = ("geometry_edge", "geometry_face", "datum_vector", "datum_plane")


class CoordinateSystemDialog(QDialog):
    """Create a coordinate system while previewing picked origins and directions."""

    apply_requested = pyqtSignal(object)
    pick_requested = pyqtSignal(object, object, object)
    cancel_pick_requested = pyqtSignal()

    def __init__(self, default_name="CSYS-1", existing_names=(), parent=None, units=None):
        """Build the coordinate-system definition with canonical editor controls."""
        super().__init__(parent)
        units = units or getattr(getattr(parent, "controllers", None), "units", None)
        self.existing_names = tuple(existing_names)
        self.setWindowTitle("Create Coordinate System")
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMinimumWidth(760)

        root = dialog_layout(self)

        self.name = QLineEdit(default_name)
        apply_primary_control_height(self.name)
        self.kind = ChevronComboBox()
        self.kind.setMinimumWidth(0)
        self.kind.addItems(("Rectangular", "Cylindrical"))
        apply_primary_control_height(self.kind)
        root.addWidget(
            field_row(
                field_block("Name", self.name),
                field_block("Type", self.kind),
            )
        )

        root.addWidget(SectionHeading("Coordinate System Definition"))
        self.origin = XYZPicker(
            allowed=_POINT_KINDS,
            value_kind="point",
            suffix=units.symbol("length") if units is not None else "",
        )
        self.axis_1 = XYZPicker(
            (1.0, 0.0, 0.0),
            allowed=_DIRECTION_KINDS,
            value_kind="direction",
        )
        self.axis_2 = XYZPicker(
            (0.0, 1.0, 0.0),
            allowed=_DIRECTION_KINDS,
            value_kind="direction",
        )
        for widget in (self.origin, self.axis_1, self.axis_2):
            widget.pick_requested.connect(self.pick_requested)
            widget.cancel_requested.connect(self.cancel_pick_requested)

        root.addWidget(field_block("Origin", self.origin))
        self.axis_1_field = field_block("X direction", self.axis_1)
        self.axis_2_field = field_block("Y direction", self.axis_2)
        root.addWidget(field_row(self.axis_1_field, self.axis_2_field))
        root.addStretch(1)
        self.kind.currentTextChanged.connect(self._update_labels)

        buttons = dialog_buttons(include_apply=True, close_instead_of_cancel=True)
        buttons.accepted.connect(lambda: self._commit(True))
        apply_button = buttons.button(QDialogButtonBox.StandardButton.Apply)
        if apply_button is not None:
            apply_button.clicked.connect(lambda: self._commit(False))
        buttons.rejected.connect(self.close)
        root.addWidget(buttons)

    def _update_labels(self, kind):
        """Adapt direction captions to rectangular or cylindrical semantics."""
        cylindrical = str(kind).lower().startswith("cyl")
        self.axis_1_field.set_label("Z direction" if cylindrical else "X direction")
        self.axis_2_field.set_label("R direction" if cylindrical else "Y direction")

    def values(self):
        """Return the current coordinate-system constructor values."""
        return {
            "name": self.name.text().strip(),
            "system_type": self.kind.currentText(),
            "origin": self.origin.value(),
            "axis_1": self.axis_1.value(),
            "axis_2": self.axis_2.value(),
        }

    def _commit(self, close_after):
        """Validate the current definition and emit it to the owning controller."""
        values = self.values()
        if not values["name"]:
            QMessageBox.warning(self, "Missing name", "Enter a coordinate system name.")
            return
        if not is_unique(values["name"], self.existing_names):
            QMessageBox.warning(
                self,
                "Duplicate name",
                f"A coordinate system named '{values['name']}' already exists.",
            )
            return
        first = np.asarray(values["axis_1"], dtype=float)
        second = np.asarray(values["axis_2"], dtype=float)
        if np.linalg.norm(first) <= 1.0e-12 or np.linalg.norm(second) <= 1.0e-12:
            QMessageBox.warning(self, "Invalid axes", "Axis directions must be non-zero.")
            return
        if np.linalg.norm(np.cross(first, second)) <= 1.0e-10 * np.linalg.norm(first) * np.linalg.norm(second):
            QMessageBox.warning(
                self,
                "Invalid axes",
                "The two axis directions must not be parallel.",
            )
            return
        self.apply_requested.emit(values)
        if close_after:
            self.accept()

    def closeEvent(self, event):
        """Release any outstanding viewport pick before the dialog disappears."""
        for widget in (self.origin, self.axis_1, self.axis_2):
            widget.finish_pick()
        self.cancel_pick_requested.emit()
        super().closeEvent(event)
