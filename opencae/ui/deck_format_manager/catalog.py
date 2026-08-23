"""Assemble the deck-format editor catalog and live-preview helpers."""

from __future__ import annotations

from copy import deepcopy

from .template_catalog import TEMPLATE_SPECS
from .template_language import loop_from_spec, render_template
from .tree_catalog import TREE_SPEC


GLOBAL_PAGES = {
    "general.formatting": "Formatting",
    "general.comments": "Comments",
    "general.output": "Output Style",
}


def template_spec(key: str, _label: str = "") -> dict:
    """Return the explicit template specification for one concrete tree leaf."""
    try:
        return TEMPLATE_SPECS[key]
    except KeyError as exc:
        raise KeyError(f"No deck template is registered for '{key}'") from exc


def format_preview_value(value: object, float_format: str = ".6g") -> str:
    """Format floating-point examples while preserving identifiers and strings."""
    if isinstance(value, float):
        return format(value, float_format)
    return str(value)


def formatted_spec(spec: dict, float_format: str = ".6g") -> dict:
    """Return a preview-only copy with numeric examples formatted consistently."""
    result = deepcopy(spec)
    result["fields"] = tuple(
        (name, description, format_preview_value(example, float_format))
        for name, description, example in tuple(spec.get("fields", ()))
    )
    loops = []
    for loop in spec.get("loops", ()):
        item = deepcopy(loop)
        item["fields"] = tuple(
            (name, description, format_preview_value(example, float_format))
            for name, description, example in tuple(loop.get("fields", ()))
        )
        item["examples"] = tuple(
            {
                key: format_preview_value(value, float_format)
                for key, value in example.items()
            }
            for example in tuple(loop.get("examples", ()))
        )
        loops.append(item)
    result["loops"] = tuple(loops)
    return result


def render_preview(
    template: str,
    spec: dict,
    *,
    float_format: str = ".6g",
) -> str:
    """Render a representative block using the selected floating-point format."""
    preview = formatted_spec(spec, float_format)
    values = {
        name: example
        for name, _description, example in tuple(preview.get("fields", ()))
    }
    loops = tuple(loop_from_spec(item) for item in preview.get("loops", ()))
    return render_template(template, values, loops)


__all__ = [
    "GLOBAL_PAGES",
    "TREE_SPEC",
    "format_preview_value",
    "formatted_spec",
    "render_preview",
    "template_spec",
]
