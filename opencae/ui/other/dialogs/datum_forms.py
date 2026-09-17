"""Builds reusable labelled controls for Datum Point/Vector/Plane method pages."""

from __future__ import annotations

from opencae.ui.components import ControlPickReference
from opencae.ui.primitives.selects import SelectForm
from opencae.ui.primitives.checks import CheckForm
from opencae.ui.components.field_stack import FieldStack
from opencae.ui.components.controls import ControlNumericUnit
from opencae.ui.primitives.inputs.geometry import apply_primary_input_geometry

def page(rows):
    """Return one datum method page using the canonical label-above field stack."""
    stack = FieldStack()
    for label, control in rows:
        stack.addRow(label, control)
    return stack


def number(value=0.0, minimum=-1e15, maximum=1e15, suffix=""):
    """Return a datum numeric editor with an optional fixed unit segment."""
    return ControlNumericUnit(
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
    return ControlPickReference(tuple(expanded))


def choice(values):
    """Return a canonical chevron combo for finite datum options."""
    control = SelectForm()
    control.setMinimumWidth(0)
    control.addItems(values)
    apply_primary_input_geometry(control)
    return control


def check(text="", checked=False):
    """Return a datum checkbox with the requested initial state."""
    return CheckForm(text, checked=checked)


def csys_choice(systems):
    """Return a coordinate-system combo storing the geometry needed by datum math."""
    control = SelectForm()
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
    apply_primary_input_geometry(control)
    return control
