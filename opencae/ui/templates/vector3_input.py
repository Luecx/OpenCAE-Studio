"""Provides the canonical segmented three-component numeric editor."""

from __future__ import annotations

from PyQt6.QtCore import QSignalBlocker, pyqtSignal
from PyQt6.QtWidgets import QDoubleSpinBox, QHBoxLayout, QWidget

from .control_metrics import apply_primary_control_height


class Vector3Input(QWidget):
    """Edit three numeric components in one aligned 40 px segmented control."""

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
    ):
        """Build three equal-width editors with compact component prefixes."""
        super().__init__(parent)
        self.setObjectName("Vector3Input")
        apply_primary_control_height(self)

        values = tuple(float(component) for component in value)
        captions = tuple(str(label) for label in labels)
        if len(values) != 3 or len(captions) != 3:
            raise ValueError("Vector3Input requires exactly three values and labels")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.editors: list[QDoubleSpinBox] = []
        object_names = ("XYZFirst", "XYZMiddle", "XYZLast")
        for caption, component, object_name in zip(
            captions,
            values,
            object_names,
            strict=True,
        ):
            editor = QDoubleSpinBox()
            editor.setObjectName(object_name)
            editor.setMinimumWidth(0)
            editor.setRange(float(minimum), float(maximum))
            editor.setDecimals(int(decimals))
            editor.setValue(component)
            editor.setPrefix(f"{caption}: ")
            apply_primary_control_height(editor)
            editor.valueChanged.connect(lambda _value: self.changed.emit())
            self.editors.append(editor)
            layout.addWidget(editor, 1)

    def value(self) -> tuple[float, float, float]:
        """Return the current three components in display order."""
        return tuple(editor.value() for editor in self.editors)

    def set_value(self, value) -> None:
        """Replace all components without emitting intermediate change signals."""
        values = tuple(float(component) for component in value)
        if len(values) != 3:
            raise ValueError("A vector requires exactly three components")
        blockers = [QSignalBlocker(editor) for editor in self.editors]
        for editor, component in zip(self.editors, values, strict=True):
            editor.setValue(component)
        del blockers
