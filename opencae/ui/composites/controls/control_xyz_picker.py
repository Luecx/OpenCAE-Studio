"""Segmented XYZ control with optional viewport picking."""

from __future__ import annotations

from PyQt6.QtCore import QSize, QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

from opencae.ui.core.icon_factory import IconKind, make_icon
from opencae.ui.core.metrics import FIELD_LABEL_SPACING
from opencae.ui.core.theme import PALETTE
from opencae.ui.primitives.buttons.button_inline_toggle import ButtonInlineToggle
from opencae.ui.primitives.inputs.geometry import apply_primary_input_geometry
from opencae.ui.primitives.inputs.input_form_number import InputFormNumber
from opencae.ui.primitives.labels import LabelBody


class ControlXYZPicker(QWidget):
    pick_requested = pyqtSignal(object, object, object)
    cancel_requested = pyqtSignal()
    changed = pyqtSignal()

    def __init__(
        self,
        values=(0.0, 0.0, 0.0),
        *,
        allowed=(),
        value_kind="point",
        suffix="",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.allowed = tuple(allowed)
        self.value_kind = str(value_kind)
        self.setObjectName("XYZPicker")
        self.setMinimumWidth(0)
        apply_primary_input_geometry(self)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        unit = str(suffix or "").strip()
        self.editors: list[InputFormNumber] = []
        segment_names = (
            "XYZFirst",
            "XYZMiddle",
            "XYZLastWithUnit" if unit else "XYZLast",
        )
        for axis, value, object_name in zip("XYZ", values, segment_names):
            editor = InputFormNumber(
                float(value),
                minimum=-1.0e30,
                maximum=1.0e30,
                decimals=8,
                prefix=f"{axis}: ",
                object_name=object_name,
            )
            editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            editor.valueChanged.connect(lambda _value: self.changed.emit())
            self.editors.append(editor)
            layout.addWidget(editor, 1)

        self.unit_label = None
        if unit:
            self.unit_label = LabelBody(unit, object_name="PrimaryUnitLabel")
            self.unit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            apply_primary_input_geometry(self.unit_label)
            layout.addWidget(self.unit_label)

        self.pick_button = ButtonInlineToggle(
            icon=make_icon(IconKind.PICK, 18, PALETTE["text"]),
            tooltip="Pick this value in the viewport",
            object_name="InlinePickButton",
            parent=self,
        )
        self.pick_button.setIconSize(QSize(18, 18))
        self.pick_button.setAccessibleName("Pick in viewport")
        self.pick_button.setEnabled(bool(self.allowed))
        self.pick_button.toggled.connect(self._toggle_pick)
        layout.addSpacing(FIELD_LABEL_SPACING)
        layout.addWidget(self.pick_button)
        self.setFocusProxy(self.editors[0])

    def value(self):
        return tuple(editor.value() for editor in self.editors)

    def set_value(self, value):
        values = tuple(float(component) for component in value)
        if len(values) != 3:
            raise ValueError("An XYZ value requires exactly three components")
        for editor, component in zip(self.editors, values):
            blocker = QSignalBlocker(editor)
            editor.setValue(component)
            del blocker
        self.changed.emit()

    def finish_pick(self):
        if self.pick_button.isChecked():
            blocker = QSignalBlocker(self.pick_button)
            self.pick_button.setChecked(False)
            del blocker

    def _toggle_pick(self, active):
        if not active:
            self.cancel_requested.emit()
            return
        if not self.allowed:
            self.finish_pick()
            return
        self.pick_requested.emit(self.allowed, self._apply_reference, self.finish_pick)

    def _apply_reference(self, reference):
        if not reference:
            self.finish_pick()
            return
        if self.value_kind == "direction":
            value = reference.get("direction") or reference.get("normal")
        else:
            value = reference.get("point") or reference.get("origin")
        if value is not None:
            self.set_value(value)
        self.finish_pick()
