from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from PyQt6.QtWidgets import QCheckBox, QDoubleSpinBox, QLineEdit, QSpinBox, QWidget

from .file_path import FilePathEditor
from .widgets import ChevronComboBox, ReferenceSelector

FIELD_WIDTH = 316


@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str
    kind: str = "text"
    default: Any = ""
    choices: tuple[Any, ...] = ()
    minimum: float = -1e12
    maximum: float = 1e12
    decimals: int = 4
    file_filter: str = "All files (*.*)"
    create_callback: Callable[[QWidget, Callable[[object], None]], None] | None = None
    pick_callback: Callable | None = None
    read_only: bool = False
    quantity: str | None = None


def create_editor(spec: FieldSpec, unit_system=None) -> QWidget:
    if spec.kind == "choice":
        widget = ChevronComboBox(); widget.addItems(spec.choices); widget.setCurrentText(str(spec.default))
    elif spec.kind == "reference":
        widget = ReferenceSelector(spec.choices, spec.default, spec.create_callback, spec.pick_callback)
    elif spec.kind == "int":
        widget = QSpinBox()
        lower = max(-2_147_483_648, int(spec.minimum))
        upper = min(2_147_483_647, int(spec.maximum))
        widget.setRange(lower, upper)
        widget.setValue(max(lower, min(upper, int(spec.default))))
    elif spec.kind == "float":
        widget = QDoubleSpinBox(); widget.setRange(spec.minimum, spec.maximum); widget.setDecimals(spec.decimals); widget.setValue(float(spec.default))
    elif spec.kind == "bool":
        widget = QCheckBox(); widget.setChecked(bool(spec.default))
    elif spec.kind == "file":
        widget = FilePathEditor(str(spec.default), spec.file_filter)
    else:
        widget = QLineEdit(str(spec.default)); widget.setReadOnly(spec.read_only)
    if spec.quantity and unit_system is not None and isinstance(widget, (QSpinBox, QDoubleSpinBox)):
        widget.setSuffix(f" {unit_system.symbol(spec.quantity)}")
    if not isinstance(widget, QCheckBox):
        widget.setMinimumWidth(FIELD_WIDTH)
    return widget


def editor_value(widget: QWidget):
    if isinstance(widget, ChevronComboBox): return widget.currentText()
    if isinstance(widget, ReferenceSelector): return widget.currentValue()
    if isinstance(widget, QSpinBox): return widget.value()
    if isinstance(widget, QDoubleSpinBox): return widget.value()
    if isinstance(widget, QCheckBox): return widget.isChecked()
    if isinstance(widget, FilePathEditor): return widget.text()
    if isinstance(widget, QLineEdit): return widget.text().strip()
    return None
