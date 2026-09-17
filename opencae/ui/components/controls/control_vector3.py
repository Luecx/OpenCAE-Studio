"""Three-component numeric control composed from form-number primitives."""

from __future__ import annotations

from PyQt6.QtCore import QSignalBlocker, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QWidget

from opencae.ui.primitives.inputs.input_form_number import InputFormNumber
from opencae.ui.primitives.inputs.geometry import apply_primary_input_geometry


class ControlVector3(QWidget):
    changed = pyqtSignal()

    def __init__(
        self,
        value=(0.0, 0.0, 0.0),
        *,
        labels=("X", "Y", "Z"),
        minimum=-1.0e30,
        maximum=1.0e30,
        decimals=7,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ControlVector3")
        apply_primary_input_geometry(self)
        values = tuple(float(component) for component in value)
        captions = tuple(str(label) for label in labels)
        if len(values) != 3 or len(captions) != 3:
            raise ValueError("ControlVector3 requires exactly three values and labels")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.editors: list[InputFormNumber] = []
        object_names = ("XYZFirst", "XYZMiddle", "XYZLast")
        for caption, component, object_name in zip(captions, values, object_names, strict=True):
            editor = InputFormNumber(
                component,
                minimum=minimum,
                maximum=maximum,
                decimals=decimals,
                prefix=f"{caption}: ",
                object_name=object_name,
            )
            editor.valueChanged.connect(lambda _value: self.changed.emit())
            self.editors.append(editor)
            layout.addWidget(editor, 1)

    def value(self) -> tuple[float, float, float]:
        return tuple(editor.value() for editor in self.editors)

    def set_value(self, value) -> None:
        values = tuple(float(component) for component in value)
        if len(values) != 3:
            raise ValueError("A vector requires exactly three components")
        blockers = [QSignalBlocker(editor) for editor in self.editors]
        for editor, component in zip(self.editors, values, strict=True):
            editor.setValue(component)
        del blockers
