"""Assemble the UI-only deck-format editor catalog and preview helpers."""

from __future__ import annotations

from collections import defaultdict

from .template_catalog import TEMPLATE_SPECS
from .tree_catalog import TREE_SPEC


GLOBAL_PAGES = {
    "general.formatting": "Formatting",
    "general.comments": "Comments",
    "general.output": "Output Style",
}


def template_spec(key: str, label: str) -> dict:
    """Return a representative template specification for one tree leaf."""
    if key in TEMPLATE_SPECS:
        return TEMPLATE_SPECS[key]
    if key.startswith("mesh.elements."):
        return _element_template_spec(label)
    field_name = label.lower().replace(" ", "_").replace("-", "_") + "_name"
    return {
        "template": f"*{label.upper().replace(' ', '')}, NAME={{{field_name}}}",
        "fields": ((field_name, f"{label} name", label.upper().replace(" ", "_")),),
    }


def render_preview(
    template: str,
    fields: tuple[tuple[str, str, str], ...],
    *,
    repeat_rows: tuple[dict[str, str], ...] = (),
    repeat: bool = False,
) -> str:
    """Render a sample block, optionally repeating all data lines after the keyword."""
    values = defaultdict(lambda: "…")
    values.update({name: example for name, _description, example in fields})
    if repeat and repeat_rows and "\n" in template:
        keyword, data = template.split("\n", 1)
        lines = [_format_template(keyword, values)]
        for row in repeat_rows:
            row_values = defaultdict(lambda: "…", values)
            row_values.update(row)
            lines.append(_format_template(data, row_values))
        return "\n".join(lines)
    return _format_template(template, values)


def _element_template_spec(label: str) -> dict:
    """Describe one canonical element-family record with repeated element rows."""
    example_type = "".join(character for character in label.upper() if character.isalnum())
    return {
        "template": "*ELEMENT, TYPE={element_type}\n{element_id}, {connectivity}",
        "fields": (
            ("element_type", f"Deck element type used for {label}", example_type),
            ("element_id", "Solver element identifier", "42"),
            ("connectivity", "Ordered solver node connectivity", "101, 102, 103, 104"),
        ),
        "repeatable": True,
        "repeat_default": True,
        "repeat_fields": ("element_id", "connectivity"),
        "repeat_examples": (
            {"element_id": "42", "connectivity": "101, 102, 103, 104"},
            {"element_id": "43", "connectivity": "102, 105, 106, 103"},
        ),
    }


def _format_template(template: str, values) -> str:
    """Format one preview fragment without making invalid in-progress text fatal."""
    try:
        return template.format_map(values)
    except (ValueError, KeyError):
        return template


__all__ = ["GLOBAL_PAGES", "TREE_SPEC", "render_preview", "template_spec"]
