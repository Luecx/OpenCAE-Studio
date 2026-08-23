"""Builds reusable labelled controls for Datum Point/Vector/Plane method pages."""

from __future__ import annotations

from PyQt6.QtWidgets import QCheckBox

from opencae.ui.core.widgets import ChevronComboBox, PickReference
from opencae.ui.templates import FieldStack, NumericUnitInput, apply_primary_control_height


def page(rows):
    """Return one datum method page using the canonical label-above field stack."""
    stack = FieldStack()
    for label, control in rows:
        stack.addRow(label, control)
    return stack


def number(value=0.0, minimum=-1e15, maximum=1e15, suffix=""):
    """Return a datum numeric editor with an optional fixed unit segment."""
    return NumericUnitInput(
        value,
        str(suffix or "").strip(),
        minimum=minimum,
        maximum=maximum,
        decimals=8,
    )


def references(*allowed):
    """Return a transient viewport-reference field accepting the requested kinds."""
    expanded = []
    for value in allowed:
        group = (
            ("geometry_vertex", "datum_point", "reference_point")
            if value == "point"
            else (value,)
        )
        for kind in group:
            if kind not in expanded:
                expanded.append(kind)
    return PickReference(tuple(expanded))


def choice(values):
    """Return a canonical chevron combo for finite datum options."""
    control = ChevronComboBox()
    control.setMinimumWidth(0)
    control.addItems(values)
    apply_primary_control_height(control)
    return control


def check(text="", checked=False):
    """Return a datum checkbox with the requested initial state."""
    control = QCheckBox(text)
    control.setChecked(checked)
    return control


def csys_choice(systems):
    """Return a coordinate-system combo storing the geometry needed by datum math."""
    control = ChevronComboBox()
    control.setMinimumWidth(0)
    control.addItem(
        "Global",
        {
            "name": "Global",
            "origin": (0, 0, 0),
            "axis_1": (1, 0, 0),
            "axis_2": (0, 1, 0),
        },
    )
    for system in systems:
        control.addItem(
            system.name,
            {
                "name": system.name,
                "origin": system.origin,
                "axis_1": system.axis_1,
                "axis_2": system.axis_2,
                "system_type": system.system_type,
            },
        )
    apply_primary_control_height(control)
    return control
