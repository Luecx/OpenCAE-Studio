"""Provides the shared modeless shell for Datum Point, Vector and Plane editors."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLineEdit,
    QMessageBox,
    QStackedWidget,
)

from opencae.model.naming import is_unique
from opencae.ui.core.widgets import ChevronComboBox
from opencae.ui.core.widgets.pick_reference import PickReference
from opencae.ui.core.widgets.xyz_picker import XYZPicker
from opencae.ui.templates import (
    SectionHeading,
    apply_close_buttons,
    apply_primary_control_height,
    dialog_layout,
    field_block,
    field_row,
)


class DatumDialogBase(QDialog):
    """Own common naming, method switching, preview and pick lifecycle for datums."""

    apply_requested = pyqtSignal(object)
    preview_requested = pyqtSignal(object)
    reference_preview_requested = pyqtSignal(object)
    pick_requested = pyqtSignal(object, object, object)
    cancel_pick_requested = pyqtSignal()

    def __init__(self, title, methods, default_name, existing_names, parent=None):
        """Build the common datum header, method selector, stacked definition and actions."""
        super().__init__(parent)
        self.existing_names = tuple(existing_names)
        self.setWindowTitle(title)
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMinimumWidth(680)

        layout = dialog_layout(self)
        self.name = QLineEdit(default_name)
        apply_primary_control_height(self.name)
        self.method = ChevronComboBox()
        self.method.setMinimumWidth(0)
        self.method.addItems(methods)
        apply_primary_control_height(self.method)
        layout.addWidget(
            field_row(
                field_block("Name", self.name),
                field_block("Method", self.method),
            )
        )

        layout.addWidget(SectionHeading("Datum Definition"))
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        buttons = apply_close_buttons()
        apply_button = buttons.button(QDialogButtonBox.StandardButton.Apply)
        if apply_button is not None:
            apply_button.clicked.connect(self._apply)
        buttons.rejected.connect(self.close)
        layout.addWidget(buttons)

        self.method.currentIndexChanged.connect(self.stack.setCurrentIndex)
        self.method.currentIndexChanged.connect(self._cancel_reference_picks)
        self.method.currentIndexChanged.connect(self.emit_preview)
        self.method.currentIndexChanged.connect(self.emit_reference_preview)
        self.name.textChanged.connect(self.emit_preview)

    def add_page(self, page):
        """Add one method page and wire all generic preview/picking controls below it."""
        self.stack.addWidget(page)
        for child in page.findChildren(QComboBox):
            child.currentIndexChanged.connect(self.emit_preview)
        for child in page.findChildren(QLineEdit):
            child.textChanged.connect(self.emit_preview)
        for child in page.findChildren(QAbstractSpinBox):
            child.editingFinished.connect(self.emit_preview)
        for child in page.findChildren(PickReference):
            child.pick_requested.connect(self.pick_requested)
            child.cancel_requested.connect(self.cancel_pick_requested)
            child.changed.connect(self._reference_changed)
        for child in page.findChildren(XYZPicker):
            child.pick_requested.connect(self.pick_requested)
            child.cancel_requested.connect(self.cancel_pick_requested)
            child.changed.connect(self.emit_preview)

    def _reference_changed(self, *_):
        """Refresh both datum geometry and persistent source-reference previews."""
        self.emit_preview()
        self.emit_reference_preview()

    def selected_references(self):
        """Return all currently populated transient references on the active method page."""
        page = self.stack.currentWidget()
        if page is None:
            return ()
        result = []
        for child in page.findChildren(PickReference):
            reference = child.reference()
            if reference:
                result.append(reference)
        return tuple(result)

    def emit_reference_preview(self, *_):
        """Publish active source references for persistent viewport highlighting."""
        self.reference_preview_requested.emit(self.selected_references())

    def _cancel_reference_picks(self, *_):
        """End every transient picker before switching datum construction method."""
        for child in self.findChildren(PickReference):
            child._pick_finished()
        for child in self.findChildren(XYZPicker):
            child.finish_pick()
        self.cancel_pick_requested.emit()

    def values(self):
        """Return subclass-specific datum constructor values."""
        raise NotImplementedError

    def emit_preview(self, *_):
        """Publish a valid partial definition while suppressing incomplete method states."""
        try:
            self.preview_requested.emit(self.values())
        except (KeyError, TypeError, ValueError):
            return

    def _apply(self):
        """Validate naming and method completeness before emitting a datum definition."""
        name = self.name.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing name", "Enter a datum name.")
            return
        if not is_unique(name, self.existing_names):
            QMessageBox.warning(
                self,
                "Duplicate name",
                f"A datum named '{name}' already exists.",
            )
            return
        try:
            values = self.values()
        except Exception as exc:
            QMessageBox.warning(self, "Incomplete definition", str(exc))
            return
        self.apply_requested.emit(values)
