"""Defines declarative field specs and their canonical editor widgets."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from PyQt6.QtWidgets import QCheckBox, QDoubleSpinBox, QLineEdit, QSpinBox, QWidget

from opencae.ui.composites.controls import (
    ControlFilePath,
    ControlNumericUnit,
    ControlReferenceSelector,
)
from opencae.ui.primitives.checks import CheckForm
from opencae.ui.primitives.inputs.input_form_integer import InputFormInteger
from opencae.ui.primitives.inputs.input_form_text import InputFormText
from opencae.ui.primitives.selects import SelectForm


class FieldKind(StrEnum):
    """Supported primitive/composite editor families for declarative fields."""

    TEXT = "text"
    CHOICE = "choice"
    REFERENCE = "reference"
    INTEGER = "int"
    FLOAT = "float"
    BOOLEAN = "bool"
    FILE = "file"


@dataclass(frozen=True)
class FieldSpec:
    """Describe one simple dialog field independently of its Qt editor class."""

    key: str
    label: str
    kind: FieldKind | str = FieldKind.TEXT
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
    kind = FieldKind(spec.kind)
    if kind is FieldKind.CHOICE:
        widget = SelectForm()
        widget.addItems(str(value) for value in spec.choices)
        widget.setCurrentText(str(spec.default))
    elif kind is FieldKind.REFERENCE:
        widget = ControlReferenceSelector(
            spec.choices,
            spec.default,
            spec.create_callback,
            spec.pick_callback,
        )
    elif kind is FieldKind.INTEGER:
        lower = max(-2_147_483_648, int(spec.minimum))
        upper = min(2_147_483_647, int(spec.maximum))
        value = max(lower, min(upper, int(spec.default)))
        widget = InputFormInteger(value, minimum=lower, maximum=upper)
        if spec.suffix:
            widget.setSuffix(spec.suffix)
    elif kind is FieldKind.FLOAT:
        widget = ControlNumericUnit(
            float(spec.default),
            str(spec.suffix or "").strip(),
            minimum=spec.minimum,
            maximum=spec.maximum,
            decimals=spec.decimals,
        )
    elif kind is FieldKind.BOOLEAN:
        widget = CheckForm(checked=bool(spec.default))
    elif kind is FieldKind.FILE:
        widget = ControlFilePath(str(spec.default), spec.file_filter)
    else:
        widget = InputFormText(str(spec.default), read_only=spec.read_only)

    widget.setMinimumWidth(0)
    return widget


def editor_value(widget: QWidget):
    """Extract the normalized Python value from a generic field editor."""
    if isinstance(widget, SelectForm):
        return widget.currentText()
    if isinstance(widget, ControlReferenceSelector):
        return widget.currentValue()
    if isinstance(widget, ControlNumericUnit):
        return widget.value()
    if isinstance(widget, QSpinBox):
        return widget.value()
    if isinstance(widget, QDoubleSpinBox):
        return widget.value()
    if isinstance(widget, QCheckBox):
        return widget.isChecked()
    if isinstance(widget, ControlFilePath):
        return widget.text()
    if isinstance(widget, QLineEdit):
        return widget.text().strip()
    return None
