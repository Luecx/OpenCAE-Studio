"""Provides the ordered shared-step list editor."""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QHBoxLayout, QListWidget

from opencae.ui.templates import SectionHeading, button, dialog_buttons, dialog_layout


class StepReorderDialog(QDialog):
    """Reorder shared analysis steps while preserving their visible names."""

    def __init__(self, names, parent=None):
        """Build the ordered list and compact move actions."""
        super().__init__(parent)
        self.setWindowTitle("Reorder Steps")
        self.setMinimumSize(640, 440)

        root = dialog_layout(self)
        root.addWidget(SectionHeading("Step Order"))
        self.list = QListWidget()
        self.list.addItems(names)
        root.addWidget(self.list, 1)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(8)
        up = button("Move Up")
        down = button("Move Down")
        up.clicked.connect(lambda: self._move(-1))
        down.clicked.connect(lambda: self._move(1))
        actions.addWidget(up)
        actions.addWidget(down)
        actions.addStretch(1)
        root.addLayout(actions)

        buttons = dialog_buttons()
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _move(self, offset):
        """Move the current step by one relative list position when possible."""
        row = self.list.currentRow()
        target = row + offset
        if row < 0 or target < 0 or target >= self.list.count():
            return
        item = self.list.takeItem(row)
        self.list.insertItem(target, item)
        self.list.setCurrentRow(target)

    def order(self):
        """Return the visible step names in their current order."""
        return [self.list.item(index).text() for index in range(self.list.count())]
