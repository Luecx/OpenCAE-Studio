"""Provides a compact read-only reference field with viewport pick and clear actions."""

from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLineEdit, QToolButton, QWidget

from opencae.ui.core.icon_factory import IconKind, make_icon
from opencae.ui.core.theme import PALETTE
from opencae.ui.templates import apply_inline_action_size, apply_primary_control_height


class PickReference(QWidget):
    """Store one transient viewport reference selected from an allowed kind set."""

    pick_requested = pyqtSignal(object, object, object)
    cancel_requested = pyqtSignal()
    changed = pyqtSignal()

    def __init__(self, allowed, parent=None):
        """Build the read-only summary plus equal-height pick/clear actions."""
        super().__init__(parent)
        self.allowed = tuple(allowed)
        self._reference = None
        self.setMinimumWidth(0)
        apply_primary_control_height(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.text = QLineEdit()
        self.text.setObjectName("CompositeFieldEdit")
        self.text.setReadOnly(True)
        self.text.setPlaceholderText("Not selected")
        self.text.setMinimumWidth(0)
        apply_primary_control_height(self.text)

        self.pick = QToolButton()
        self.pick.setIcon(make_icon(IconKind.PICK, 18, PALETTE["text"]))
        self.pick.setIconSize(QSize(18, 18))
        self.pick.setToolTip("Pick in viewport")
        self.pick.setAccessibleName("Pick in viewport")
        self.pick.setObjectName("InlinePickButton")
        self.pick.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pick.setCheckable(True)
        apply_inline_action_size(self.pick)

        self.clear_button = QToolButton()
        self.clear_button.setText("×")
        self.clear_button.setToolTip("Clear reference")
        self.clear_button.setAccessibleName("Clear reference")
        self.clear_button.setObjectName("InlineClearButton")
        self.clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_inline_action_size(self.clear_button)

        self.pick.clicked.connect(self._pick)
        self.clear_button.clicked.connect(lambda: self.set_reference(None))
        layout.addWidget(self.text, 1)
        layout.addWidget(self.pick)
        layout.addWidget(self.clear_button)

    def set_reference(self, reference):
        """Replace the stored reference and update the visible summary."""
        self.pick.setChecked(False)
        self._reference = dict(reference) if reference else None
        self.text.setText(self._reference.get("name", "") if self._reference else "")
        self.changed.emit()

    def reference(self):
        """Return a defensive copy of the current viewport reference."""
        return dict(self._reference) if self._reference else None

    def _pick(self, checked=False):
        """Begin or cancel selection through the owning dialog/controller."""
        if not checked:
            self.cancel_requested.emit()
            return
        self.pick_requested.emit(self.allowed, self.set_reference, self._pick_finished)

    def _pick_finished(self):
        """Clear the visual checked state when a viewport session finishes."""
        self.pick.setChecked(False)
