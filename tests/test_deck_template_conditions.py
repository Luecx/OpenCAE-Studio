"""Regression tests for conditional input-deck template rendering."""

from __future__ import annotations

import pytest

from opencae.deck_formats.template_language import render_runtime_template


def render(template: str, **values) -> str:
    """Render a scalar-only template for concise condition tests."""
    return render_runtime_template(template, values, {})


def test_if_can_distinguish_zero_from_free_none_dof():
    """A prescribed zero is emitted while a free ``None`` component is omitted."""
    template = (
        "*BOUNDARY\n"
        "{if ux is not none}\n"
        "SET, 1, 1, {ux}\n"
        "{endif}\n"
        "{if uy is not none}\n"
        "SET, 2, 2, {uy}\n"
        "{endif}"
    )
    assert render(template, ux=0.0, uy=None) == "*BOUNDARY\nSET, 1, 1, 0.0"


def test_if_elif_else_and_boolean_operators_are_supported():
    template = (
        "{if mode == 'fixed' and enabled}\n"
        "FIXED\n"
        "{elif mode == 'symmetry'}\n"
        "SYMMETRY\n"
        "{else}\n"
        "FREE\n"
        "{endif}"
    )
    assert render(template, mode="fixed", enabled=True) == "FIXED"
    assert render(template, mode="symmetry", enabled=False) == "SYMMETRY"
    assert render(template, mode="other", enabled=False) == "FREE"


def test_conditions_work_inside_loops_on_dotted_fields():
    template = (
        "{for row in rows}\n"
        "{if row.value is not none}\n"
        "{row.target}, {row.dof}, {row.value}\n"
        "{endif}\n"
        "{endfor}"
    )
    rows = [
        {"target": "A", "dof": 1, "value": 0.0},
        {"target": "A", "dof": 2, "value": None},
        {"target": "A", "dof": 3, "value": -2.5},
    ]
    assert render_runtime_template(template, {}, {"rows": rows}) == (
        "A, 1, 0.0\nA, 3, -2.5"
    )


def test_nested_conditions_render_safely():
    template = (
        "{if enabled}\n"
        "outer\n"
        "{if value >= 2}\n"
        "inner\n"
        "{endif}\n"
        "{endif}"
    )
    assert render(template, enabled=True, value=2) == "outer\ninner"


def test_invalid_conditional_structure_is_rejected():
    with pytest.raises(ValueError, match="Missing \\{endif\\}"):
        render("{if enabled}\nvalue", enabled=True)
    with pytest.raises(ValueError, match="Unexpected conditional terminator"):
        render("{else}\nvalue")
