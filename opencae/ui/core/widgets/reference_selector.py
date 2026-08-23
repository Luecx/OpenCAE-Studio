"""Provides a reusable reference selector with optional create and pick actions."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QToolButton, QWidget

from opencae.ui.core.dialog_lifecycle import activate_dialog
from opencae.ui.core.icon_factory import IconKind, make_icon
from opencae.ui.core.theme import PALETTE
from opencae.ui.templates import (
    apply_inline_action_size,
    apply_primary_control_height,
)

from .chevron_combo import ChevronComboBox


class ReferenceSelector(QWidget):
    """Select an object reference and optionally create or pick a new target."""

    value_changed = pyqtSignal(object)

    def __init__(
        self,
        values: Iterable = (),
        current=None,
        create_callback: Callable | None = None,
        pick_callback: Callable | None = None,
        parent=None,
    ):
        """Build one reference combo with compact secondary actions."""
        super().__init__(parent)
        apply_primary_control_height(self)
        self.setMinimumWidth(0)

        self.combo = ChevronComboBox()
        self.combo.setObjectName("ReferenceCombo")
        self.combo.setMinimumWidth(0)
        apply_primary_control_height(self.combo)
        self._add_values(values)
        self.setCurrentValue(current)
        self.combo.currentIndexChanged.connect(
            lambda _index: self.value_changed.emit(self.currentValue())
        )

        self.add_button = QToolButton()
        self.add_button.setText("+")
        self.add_button.setObjectName("InlineAddButton")
        self.add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_button.setToolTip("Create a new referenced object")
        apply_inline_action_size(self.add_button)
        self._create_callback = create_callback
        self.add_button.setVisible(create_callback is not None)
        self.add_button.clicked.connect(self._create)

        self.pick_button = QToolButton()
        self.pick_button.setIcon(make_icon(IconKind.PICK, 16, PALETTE["text"]))
        self.pick_button.setIconSize(QSize(16, 16))
        self.pick_button.setObjectName("InlinePickButton")
        self.pick_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pick_button.setCheckable(True)
        self.pick_button.setAccessibleName("Pick in viewport")
        self.pick_button.setToolTip("Pick the referenced object in the viewport")
        apply_inline_action_size(self.pick_button)
        self._pick_callback = pick_callback
        self.pick_button.setVisible(pick_callback is not None)
        self.pick_button.clicked.connect(self._pick)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.combo, 1)
        layout.addWidget(self.pick_button, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.add_button, 0, Qt.AlignmentFlag.AlignVCenter)

    @staticmethod
    def _option(value):
        """Normalize supported reference values into display text and data."""
        if hasattr(value, "id") and hasattr(value, "name"):
            return str(value.name), str(value.id)
        if isinstance(value, tuple) and len(value) == 2:
            return str(value[0]), value[1]
        return str(value), value

    def _add_values(self, values) -> None:
        """Append normalized reference candidates to the combo box."""
        for value in values:
            label, data = self._option(value)
            self.combo.addItem(label, data)

    def currentText(self):
        """Return the visible text of the selected reference."""
        return self.combo.currentText()

    def currentData(self):
        """Return the stored data of the selected reference."""
        return self.combo.currentData()

    def currentValue(self):
        """Return the selected reference value."""
        return self.currentData()

    def current_id(self):
        """Compatibility alias for the selected reference value."""
        return self.currentData()

    def setCurrentText(self, value) -> None:
        """Select a reference by visible text."""
        self.combo.setCurrentText(str(value or ""))

    def setCurrentValue(self, value) -> None:
        """Select a reference by object, stored data, or visible text."""
        if value is None or value == "":
            return
        if hasattr(value, "id"):
            value = value.id
        index = self.combo.findData(value)
        if index < 0:
            index = self.combo.findText(str(value))
        if index >= 0:
            self.combo.setCurrentIndex(index)

    def clear(self) -> None:
        """Clear the current reference selection."""
        self.combo.setCurrentIndex(-1)
        self.value_changed.emit(self.currentValue())

    def set_values(self, values, current=None) -> None:
        """Replace available references while preserving the active value."""
        previous = self.currentValue() if current in (None, "") else current
        self.combo.blockSignals(True)
        self.combo.clear()
        self._add_values(values)
        self.setCurrentValue(previous)
        self.combo.blockSignals(False)

    def _apply_created(self, value) -> None:
        """Insert and select a value returned by a nested create dialog."""
        self.pick_button.setChecked(False)
        if not value:
            return
        label, data = self._option(value)
        index = self.combo.findData(data)
        if index < 0:
            self.combo.addItem(label, data)
            index = self.combo.count() - 1
        self.combo.setCurrentIndex(index)
        activate_dialog(self)

    def _create(self) -> None:
        """Open the configured create workflow when available."""
        if self._create_callback is not None:
            self._create_callback(self.window(), self._apply_created)

    def _pick(self) -> None:
        """Begin the configured viewport-pick workflow when available."""
        if self._pick_callback is None:
            return
        self.pick_button.setChecked(True)
        self._pick_callback(self.window(), self._apply_created)
