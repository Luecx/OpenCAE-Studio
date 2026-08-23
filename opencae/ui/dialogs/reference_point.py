"""Provides modeless reference-point creation with live viewport preview."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLineEdit, QMessageBox

from opencae.model.naming import is_unique
from opencae.ui.core.widgets import XYZPicker
from opencae.ui.templates import (
    SectionHeading,
    apply_primary_control_height,
    dialog_buttons,
    dialog_layout,
    field_block,
)

_POINT_KINDS = ("geometry_vertex", "datum_point", "reference_point")


class ReferencePointDialog(QDialog):
    """Create one reference point while keeping its current position visible."""

    apply_requested = pyqtSignal(object)
    pick_requested = pyqtSignal(object, object, object)
    cancel_pick_requested = pyqtSignal()

    def __init__(self, default_name="RP-1", existing_names=(), parent=None, units=None):
        """Build the canonical name/position editor and standard modeless actions."""
        super().__init__(parent)
        units = units or getattr(getattr(parent, "controllers", None), "units", None)
        self.existing_names = tuple(existing_names)
        self.setWindowTitle("Create Reference Point")
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMinimumWidth(620)

        root = dialog_layout(self)
        self.name = QLineEdit(default_name)
        apply_primary_control_height(self.name)
        root.addWidget(field_block("Name", self.name))

        root.addWidget(SectionHeading("Reference Point Definition"))
        self.position = XYZPicker(
            allowed=_POINT_KINDS,
            value_kind="point",
            suffix=units.symbol("length") if units is not None else "",
        )
        self.position.pick_requested.connect(self.pick_requested)
        self.position.cancel_requested.connect(self.cancel_pick_requested)
        self.position.changed.connect(self._preview)
        self.name.textChanged.connect(self._preview)
        root.addWidget(field_block("Position", self.position))
        root.addStretch(1)

        buttons = dialog_buttons(include_apply=True, close_instead_of_cancel=True)
        buttons.accepted.connect(lambda: self._commit(True))
        apply_button = buttons.button(QDialogButtonBox.StandardButton.Apply)
        if apply_button is not None:
            apply_button.clicked.connect(lambda: self._commit(False))
        buttons.rejected.connect(self.close)
        root.addWidget(buttons)

    def values(self):
        """Return the current reference-point constructor values."""
        return {"name": self.name.text().strip(), "position": self.position.value()}

    def _viewport(self):
        """Return the owning viewport when the dialog is hosted by the main window."""
        return getattr(self.parent(), "viewport", None)

    def _preview(self, *_):
        """Render the current point even before it has been committed."""
        viewport = self._viewport()
        if viewport is None:
            return
        name = self.name.text().strip() or "Reference Point"
        viewport.show_reference_point_preview(name, self.position.value())

    def _clear_preview(self):
        """Remove the temporary point preview from the viewport."""
        viewport = self._viewport()
        if viewport is not None:
            viewport.clear_reference_point_preview()

    def _commit(self, close_after):
        """Validate and publish the current point, optionally closing afterwards."""
        values = self.values()
        if not values["name"]:
            QMessageBox.warning(self, "Missing name", "Enter a reference point name.")
            return
        if not is_unique(values["name"], self.existing_names):
            QMessageBox.warning(
                self,
                "Duplicate name",
                f"A reference point named '{values['name']}' already exists.",
            )
            return
        self._clear_preview()
        self.apply_requested.emit(values)
        if close_after:
            self.accept()

    def showEvent(self, event):
        """Start the live preview as soon as the dialog becomes visible."""
        super().showEvent(event)
        self._preview()

    def closeEvent(self, event):
        """Release picker state and preview actors when the dialog closes."""
        self.position.finish_pick()
        self.cancel_pick_requested.emit()
        self._clear_preview()
        super().closeEvent(event)
