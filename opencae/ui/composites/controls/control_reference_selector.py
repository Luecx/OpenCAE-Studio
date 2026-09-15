"""Reference selector composed from one select and optional create/pick actions."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QWidget

from opencae.ui.core.dialog_lifecycle import activate_dialog
from opencae.ui.core.icon_factory import IconKind, make_icon
from opencae.ui.core.theme import PALETTE
from opencae.ui.primitives.buttons.button_inline_action import ButtonInlineAction
from opencae.ui.primitives.buttons.button_inline_toggle import ButtonInlineToggle
from opencae.ui.primitives.inputs.geometry import apply_primary_input_geometry
from opencae.ui.primitives.selects import SelectForm


class ControlReferenceSelector(QWidget):
    value_changed = pyqtSignal(object)

    def __init__(
        self,
        values: Iterable = (),
        current=None,
        create_callback: Callable | None = None,
        pick_callback: Callable | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        apply_primary_input_geometry(self)
        self.setMinimumWidth(0)
        self.combo = SelectForm()
        self.combo.setObjectName("ReferenceCombo")
        self._add_values(values)
        self.setCurrentValue(current)
        self.combo.currentIndexChanged.connect(
            lambda _index: self.value_changed.emit(self.currentValue())
        )

        self.add_button = ButtonInlineAction(
            "+",
            tooltip="Create a new referenced object",
            object_name="InlineAddButton",
            parent=self,
        )
        self._create_callback = create_callback
        self.add_button.setVisible(create_callback is not None)
        self.add_button.clicked.connect(self._create)

        self.pick_button = ButtonInlineToggle(
            icon=make_icon(IconKind.PICK, 16, PALETTE["text"]),
            tooltip="Pick the referenced object in the viewport",
            object_name="InlinePickButton",
            parent=self,
        )
        self.pick_button.setIconSize(QSize(16, 16))
        self.pick_button.setAccessibleName("Pick in viewport")
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
        if hasattr(value, "id") and hasattr(value, "name"):
            return str(value.name), str(value.id)
        if isinstance(value, tuple) and len(value) == 2:
            return str(value[0]), value[1]
        return str(value), value

    def _add_values(self, values) -> None:
        for value in values:
            label, data = self._option(value)
            self.combo.addItem(label, data)

    def currentText(self):
        return self.combo.currentText()

    def currentData(self):
        return self.combo.currentData()

    def currentValue(self):
        return self.currentData()

    def current_id(self):
        return self.currentData()

    def setCurrentText(self, value) -> None:
        self.combo.setCurrentText(str(value or ""))

    def setCurrentValue(self, value) -> None:
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
        self.combo.setCurrentIndex(-1)
        self.value_changed.emit(self.currentValue())

    def set_values(self, values, current=None) -> None:
        previous = self.currentValue() if current in (None, "") else current
        self.combo.blockSignals(True)
        self.combo.clear()
        self._add_values(values)
        self.setCurrentValue(previous)
        self.combo.blockSignals(False)

    def _apply_created(self, value) -> None:
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
        if self._create_callback is not None:
            self._create_callback(self.window(), self._apply_created)

    def _pick(self) -> None:
        if self._pick_callback is None:
            return
        self.pick_button.setChecked(True)
        self._pick_callback(self.window(), self._apply_created)
