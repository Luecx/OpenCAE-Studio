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
    field_name = label.lower().replace(" ", "_").replace("-", "_") + "_name"
    return {
        "template": f"*{label.upper().replace(' ', '')}, NAME={{{field_name}}}",
        "fields": ((field_name, f"{label} name", label.upper().replace(" ", "_")),),
    }


def render_preview(template: str, fields: tuple[tuple[str, str, str], ...]) -> str:
    """Render a live prototype preview from the field example values."""
    values = defaultdict(lambda: "…")
    values.update({name: example for name, _description, example in fields})
    try:
        return template.format_map(values)
    except (ValueError, KeyError):
        return template


__all__ = ["GLOBAL_PAGES", "TREE_SPEC", "render_preview", "template_spec"]
