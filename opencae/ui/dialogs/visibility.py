"""Provides the modeless display-only Part topology visibility editor."""

from __future__ import annotations

from PyQt6.QtCore import QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtWidgets import QAbstractItemView, QDialog, QGridLayout, QListWidget, QListWidgetItem

from opencae.ui.core.widgets import ChevronComboBox
from opencae.ui.templates import (
    FieldLabel,
    SectionHeading,
    apply_primary_control_height,
    button,
    dialog_buttons,
    dialog_layout,
    field_block,
)

_LABELS = {
    "faces": ("Face", "Faces"),
    "cells": ("Cell", "Cells"),
    "elements": ("Element", "Elements"),
}


class VisibilityDialog(QDialog):
    """Hide or reveal display entities without mutating model or solver state."""

    mode_changed = pyqtSignal(str)
    pick_requested = pyqtSignal(str)
    cancel_pick_requested = pyqtSignal()
    show_selected_requested = pyqtSignal(str, object)
    invert_requested = pyqtSignal(str)
    show_all_requested = pyqtSignal(str)
    hide_all_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        """Build mode selection, hidden-entity list and visibility actions."""
        super().__init__(parent)
        self.setWindowTitle("Part Visibility")
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMinimumSize(640, 520)

        root = dialog_layout(self)
        hint = FieldLabel(
            "Hide display entities without changing geometry, mesh or solver output."
        )
        hint.setWordWrap(True)
        root.addWidget(hint)

        self.mode = ChevronComboBox()
        self.mode.setMinimumWidth(0)
        self.mode.addItem("Faces", "faces")
        self.mode.addItem("Cells", "cells")
        self.mode.addItem("Elements", "elements")
        apply_primary_control_height(self.mode)
        self.mode.currentIndexChanged.connect(self._mode_changed)
        root.addWidget(field_block("Entity type", self.mode))

        root.addWidget(SectionHeading("Hidden Entities"))
        self.summary = FieldLabel("0 hidden")
        root.addWidget(self.summary)
        self.items = QListWidget()
        self.items.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.items.setMinimumHeight(190)
        root.addWidget(self.items, 1)

        actions = QGridLayout()
        actions.setHorizontalSpacing(8)
        actions.setVerticalSpacing(8)

        self.add_button = button("Add from Viewport")
        self.add_button.setCheckable(True)
        self.add_button.setObjectName("PrimaryButton")
        self.add_button.setToolTip("Pick additional entities to hide")
        self.add_button.toggled.connect(self._pick_toggled)

        self.show_selected = button("Show Selected")
        self.show_selected.clicked.connect(self._show_selected)
        self.invert = button("Invert")
        self.invert.clicked.connect(
            lambda: self.invert_requested.emit(self.current_mode())
        )
        self.show_all = button("Show All")
        self.show_all.clicked.connect(
            lambda: self.show_all_requested.emit(self.current_mode())
        )
        self.hide_all = button("Hide All")
        self.hide_all.clicked.connect(
            lambda: self.hide_all_requested.emit(self.current_mode())
        )

        actions.addWidget(self.add_button, 0, 0, 1, 2)
        actions.addWidget(self.show_selected, 1, 0)
        actions.addWidget(self.invert, 1, 1)
        actions.addWidget(self.show_all, 2, 0)
        actions.addWidget(self.hide_all, 2, 1)
        root.addLayout(actions)

        buttons = dialog_buttons(close_instead_of_cancel=True)
        ok = buttons.button(buttons.StandardButton.Ok)
        if ok is not None:
            ok.hide()
        buttons.rejected.connect(self.close)
        root.addWidget(buttons)

    def current_mode(self) -> str:
        """Return the canonical entity category represented by the mode combo."""
        return str(self.mode.currentData() or "faces")

    def set_hidden(self, hidden, total: int) -> None:
        """Replace the hidden-ID list while preserving selected rows where possible."""
        values = sorted({int(value) for value in hidden})
        selected = {
            int(item.data(Qt.ItemDataRole.UserRole))
            for item in self.items.selectedItems()
        }
        self.items.clear()
        singular, plural = _LABELS[self.current_mode()]
        for value in values:
            item = QListWidgetItem(f"{singular}-{value}")
            item.setData(Qt.ItemDataRole.UserRole, value)
            self.items.addItem(item)
            item.setSelected(value in selected)
        label = singular if len(values) == 1 else plural
        self.summary.setText(
            f"{len(values):,} of {int(total):,} {label.lower()} hidden"
        )
        self.show_selected.setEnabled(bool(values))
        self.show_all.setEnabled(bool(values))
        self.hide_all.setEnabled(len(values) < int(total))

    def finish_pick(self) -> None:
        """End viewport picking and restore the Add action caption."""
        if self.add_button.isChecked():
            blocker = QSignalBlocker(self.add_button)
            self.add_button.setChecked(False)
            del blocker
        self.add_button.setText("Add from Viewport")
        self.add_button.setToolTip("Pick additional entities to hide")

    def _mode_changed(self, *_):
        """Finish an active picker before changing the visible entity category."""
        self.finish_pick()
        self.cancel_pick_requested.emit()
        self.mode_changed.emit(self.current_mode())

    def _pick_toggled(self, active: bool):
        """Start or finish viewport additions to the hidden entity set."""
        if active:
            self.add_button.setText("Finish Picking")
            self.add_button.setToolTip("Finish adding hidden entities")
            self.pick_requested.emit(self.current_mode())
        else:
            self.add_button.setText("Add from Viewport")
            self.add_button.setToolTip("Pick additional entities to hide")
            self.cancel_pick_requested.emit()

    def _show_selected(self):
        """Request revealing the currently selected hidden-list rows."""
        values = [
            int(item.data(Qt.ItemDataRole.UserRole))
            for item in self.items.selectedItems()
        ]
        if values:
            self.show_selected_requested.emit(self.current_mode(), values)

    def closeEvent(self, event):
        """Release any active viewport-pick session before closing."""
        self.cancel_pick_requested.emit()
        super().closeEvent(event)
