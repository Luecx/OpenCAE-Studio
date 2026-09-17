"""Read-only reference field with viewport pick and clear actions."""

from __future__ import annotations

from PyQt6.QtCore import QSize, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QWidget

from opencae.ui.foundation.icons import IconKind, make_icon
from opencae.ui.foundation.theme import PALETTE
from opencae.ui.primitives.buttons.button_inline_action import ButtonInlineAction
from opencae.ui.primitives.buttons.button_inline_toggle import ButtonInlineToggle
from opencae.ui.primitives.inputs.input_form_text import InputFormText
from opencae.ui.primitives.inputs.geometry import apply_primary_input_geometry


class ControlPickReference(QWidget):
    pick_requested = pyqtSignal(object, object, object)
    cancel_requested = pyqtSignal()
    changed = pyqtSignal()

    def __init__(self, allowed, parent=None) -> None:
        super().__init__(parent)
        self.allowed = tuple(allowed)
        self._reference = None
        self.setMinimumWidth(0)
        apply_primary_input_geometry(self)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.text = InputFormText(
            "",
            read_only=True,
            object_name="CompositeFieldEdit",
            parent=self,
        )
        self.text.setPlaceholderText("Not selected")

        pick_icon = make_icon(IconKind.PICK, 18, PALETTE["text"])
        self.pick = ButtonInlineToggle(
            icon=pick_icon,
            tooltip="Pick in viewport",
            object_name="InlinePickButton",
            parent=self,
        )
        self.pick.setIconSize(QSize(18, 18))
        self.pick.setAccessibleName("Pick in viewport")

        self.clear_button = ButtonInlineAction(
            "×",
            tooltip="Clear reference",
            object_name="InlineClearButton",
            parent=self,
        )
        self.clear_button.setAccessibleName("Clear reference")

        self.pick.clicked.connect(self._pick)
        self.clear_button.clicked.connect(lambda: self.set_reference(None))
        layout.addWidget(self.text, 1)
        layout.addWidget(self.pick)
        layout.addWidget(self.clear_button)

    def set_reference(self, reference):
        self.pick.setChecked(False)
        self._reference = dict(reference) if reference else None
        self.text.setText(self._reference.get("name", "") if self._reference else "")
        self.changed.emit()

    def reference(self):
        return dict(self._reference) if self._reference else None

    def _pick(self, checked=False):
        if not checked:
            self.cancel_requested.emit()
            return
        self.pick_requested.emit(self.allowed, self.set_reference, self._pick_finished)

    def _pick_finished(self):
        self.pick.setChecked(False)
