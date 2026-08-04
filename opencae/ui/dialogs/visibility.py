from __future__ import annotations

from PyQt6.QtCore import QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)


_LABELS = {
    "faces": ("Face", "Faces"),
    "cells": ("Cell", "Cells"),
    "elements": ("Element", "Elements"),
}


class VisibilityDialog(QDialog):
    """Modeless editor for display-only Part topology visibility."""

    mode_changed = pyqtSignal(str)
    pick_requested = pyqtSignal(str)
    cancel_pick_requested = pyqtSignal()
    show_selected_requested = pyqtSignal(str, object)
    invert_requested = pyqtSignal(str)
    show_all_requested = pyqtSignal(str)
    hide_all_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Part Visibility")
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMinimumWidth(420)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 12)
        root.setSpacing(10)

        root.addWidget(QLabel(
            "Hide display entities without changing geometry, mesh or solver output."
        ))

        self.mode = QComboBox()
        self.mode.addItem("Faces", "faces")
        self.mode.addItem("Cells", "cells")
        self.mode.addItem("Elements", "elements")
        self.mode.currentIndexChanged.connect(self._mode_changed)
        root.addWidget(self.mode)

        hidden_group = QGroupBox("Hidden entities")
        hidden_layout = QVBoxLayout(hidden_group)
        hidden_layout.setContentsMargins(10, 12, 10, 10)
        hidden_layout.setSpacing(8)
        self.summary = QLabel("0 hidden")
        self.summary.setObjectName("MutedLabel")
        hidden_layout.addWidget(self.summary)
        self.items = QListWidget()
        self.items.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.items.setMinimumHeight(170)
        hidden_layout.addWidget(self.items)
        root.addWidget(hidden_group)

        actions = QGridLayout()
        actions.setHorizontalSpacing(8)
        actions.setVerticalSpacing(8)

        self.add_button = QPushButton("Add from Viewport")
        self.add_button.setCheckable(True)
        self.add_button.setObjectName("PrimaryButton")
        self.add_button.setToolTip("Pick additional entities to hide")
        self.add_button.toggled.connect(self._pick_toggled)

        self.show_selected = QPushButton("Show Selected")
        self.show_selected.clicked.connect(self._show_selected)
        self.invert = QPushButton("Invert")
        self.invert.clicked.connect(lambda: self.invert_requested.emit(self.current_mode()))
        self.show_all = QPushButton("Show All")
        self.show_all.clicked.connect(lambda: self.show_all_requested.emit(self.current_mode()))
        self.hide_all = QPushButton("Hide All")
        self.hide_all.clicked.connect(lambda: self.hide_all_requested.emit(self.current_mode()))

        actions.addWidget(self.add_button, 0, 0, 1, 2)
        actions.addWidget(self.show_selected, 1, 0)
        actions.addWidget(self.invert, 1, 1)
        actions.addWidget(self.show_all, 2, 0)
        actions.addWidget(self.hide_all, 2, 1)
        root.addLayout(actions)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.close)
        root.addWidget(buttons)

    def current_mode(self) -> str:
        return str(self.mode.currentData() or "faces")

    def set_hidden(self, hidden, total: int) -> None:
        values = sorted({int(value) for value in hidden})
        selected = {int(item.data(Qt.ItemDataRole.UserRole)) for item in self.items.selectedItems()}
        self.items.clear()
        singular, plural = _LABELS[self.current_mode()]
        for value in values:
            item = QListWidgetItem(f"{singular}-{value}")
            item.setData(Qt.ItemDataRole.UserRole, value)
            self.items.addItem(item)
            item.setSelected(value in selected)
        label = singular if len(values) == 1 else plural
        self.summary.setText(f"{len(values):,} of {int(total):,} {label.lower()} hidden")
        self.show_selected.setEnabled(bool(values))
        self.show_all.setEnabled(bool(values))
        self.hide_all.setEnabled(len(values) < int(total))

    def finish_pick(self) -> None:
        if self.add_button.isChecked():
            blocker = QSignalBlocker(self.add_button)
            self.add_button.setChecked(False)
            del blocker
        self.add_button.setText("Add from Viewport")
        self.add_button.setToolTip("Pick additional entities to hide")

    def _mode_changed(self, *_):
        self.finish_pick()
        self.cancel_pick_requested.emit()
        self.mode_changed.emit(self.current_mode())

    def _pick_toggled(self, active: bool):
        if active:
            self.add_button.setText("Finish Picking")
            self.add_button.setToolTip("Finish adding hidden entities")
            self.pick_requested.emit(self.current_mode())
        else:
            self.add_button.setText("Add from Viewport")
            self.add_button.setToolTip("Pick additional entities to hide")
            self.cancel_pick_requested.emit()

    def _show_selected(self):
        values = [
            int(item.data(Qt.ItemDataRole.UserRole))
            for item in self.items.selectedItems()
        ]
        if values:
            self.show_selected_requested.emit(self.current_mode(), values)

    def closeEvent(self, event):
        self.cancel_pick_requested.emit()
        super().closeEvent(event)
