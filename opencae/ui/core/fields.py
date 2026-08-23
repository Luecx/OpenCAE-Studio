"""Defines declarative field specs and their canonical editor widgets."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from PyQt6.QtWidgets import QCheckBox, QDoubleSpinBox, QLineEdit, QSpinBox, QWidget

from opencae.ui.templates import NumericUnitInput, apply_primary_control_height

from .file_path import FilePathEditor
from .widgets import ChevronComboBox, ReferenceSelector


@dataclass(frozen=True)
class FieldSpec:
    """Describe one simple dialog field independently of its Qt editor class."""

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
    suffix: str = ""


def create_editor(spec: FieldSpec) -> QWidget:
    """Create the canonical editor for one declarative field specification."""
    if spec.kind == "choice":
        widget = ChevronComboBox()
        widget.addItems(spec.choices)
        widget.setCurrentText(str(spec.default))
        apply_primary_control_height(widget)
    elif spec.kind == "reference":
        widget = ReferenceSelector(
            spec.choices,
            spec.default,
            spec.create_callback,
            spec.pick_callback,
        )
    elif spec.kind == "int":
        widget = QSpinBox()
        lower = max(-2_147_483_648, int(spec.minimum))
        upper = min(2_147_483_647, int(spec.maximum))
        widget.setRange(lower, upper)
        widget.setValue(max(lower, min(upper, int(spec.default))))
        if spec.suffix:
            widget.setSuffix(spec.suffix)
        apply_primary_control_height(widget)
    elif spec.kind == "float":
        # Units are display metadata, so keep them in the same fixed right-hand
        # segment used by Material/Profile/Section numeric controls.
        widget = NumericUnitInput(
            float(spec.default),
            str(spec.suffix or "").strip(),
            minimum=spec.minimum,
            maximum=spec.maximum,
            decimals=spec.decimals,
        )
    elif spec.kind == "bool":
        widget = QCheckBox()
        widget.setChecked(bool(spec.default))
    elif spec.kind == "file":
        widget = FilePathEditor(str(spec.default), spec.file_filter)
    else:
        widget = QLineEdit(str(spec.default))
        widget.setReadOnly(spec.read_only)
        apply_primary_control_height(widget)

    widget.setMinimumWidth(0)
    return widget


def editor_value(widget: QWidget):
    """Extract the normalized Python value from a generic field editor."""
    if isinstance(widget, ChevronComboBox):
        return widget.currentText()
    if isinstance(widget, ReferenceSelector):
        return widget.currentValue()
    if isinstance(widget, NumericUnitInput):
        return widget.value()
    if isinstance(widget, QSpinBox):
        return widget.value()
    if isinstance(widget, QDoubleSpinBox):
        return widget.value()
    if isinstance(widget, QCheckBox):
        return widget.isChecked()
    if isinstance(widget, FilePathEditor):
        return widget.text()
    if isinstance(widget, QLineEdit):
        return widget.text().strip()
    return None
