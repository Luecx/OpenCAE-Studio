"""Assemble the UI-only deck-format editor catalog and preview helpers."""

from __future__ import annotations

from .template_catalog import TEMPLATE_SPECS
from .template_language import loop_from_spec, render_template
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
        "loops": (),
    }


def render_preview(template: str, spec: dict) -> str:
    """Render a live prototype preview using fields and explicit template loops."""
    values = {
        name: example
        for name, _description, example in tuple(spec.get("fields", ()))
    }
    loops = tuple(loop_from_spec(item) for item in spec.get("loops", ()))
    return render_template(template, values, loops)


__all__ = ["GLOBAL_PAGES", "TREE_SPEC", "render_preview", "template_spec"]
