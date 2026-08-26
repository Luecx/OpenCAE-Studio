"""Render the deliberately small declarative deck-template language."""

from __future__ import annotations

import re
from dataclasses import dataclass


_FOR_PATTERN = re.compile(
    r"^\s*\{for\s+(?P<item>[A-Za-z_]\w*)\s+in\s+(?P<collection>[A-Za-z_]\w*)\}\s*$"
)
_END_PATTERN = re.compile(r"^\s*\{endfor\}\s*$")


@dataclass(frozen=True)
class TemplateLoop:
    """Preview description for one named template collection."""

    collection: str
    item: str
    description: str
    fields: tuple[tuple[str, str, str], ...]
    examples: tuple[dict[str, object], ...]


class TemplateObject:
    """Expose dictionary values through dotted template placeholders."""

    def __init__(self, values: dict[str, object]):
        self._values = values

    def __getattr__(self, name: str):
        return self._values.get(name, "")


class TemplateContext(dict):
    """Keep partially edited templates renderable by tolerating missing values."""

    def __missing__(self, _key):
        return ""


def render_template(
    template: str,
    values: dict[str, object],
    loops: tuple[TemplateLoop, ...] = (),
) -> str:
    """Render scalar placeholders and preview loop examples."""
    collections = {loop.collection: tuple(loop.examples) for loop in loops}
    return render_runtime_template(template, values, collections)


def render_runtime_template(
    template: str,
    values: dict[str, object],
    collections: dict[str, tuple[dict[str, object], ...] | list[dict[str, object]]],
) -> str:
    """Render a template against real scalar values and collection rows."""
    context = TemplateContext(values)
    lines = template.splitlines()
    rendered, index = _render_lines(lines, 0, context, collections, stop_at_end=False)
    if index != len(lines):
        raise ValueError("Unexpected trailing template structure")
    return "\n".join(rendered)


def loop_from_spec(spec: dict) -> TemplateLoop:
    """Convert one declarative editor loop spec into a typed preview definition."""
    return TemplateLoop(
        collection=str(spec["collection"]),
        item=str(spec["item"]),
        description=str(spec.get("description", "")),
        fields=tuple(spec.get("fields", ())),
        examples=tuple(dict(item) for item in spec.get("examples", ())),
    )


def loop_skeleton(loop: TemplateLoop) -> str:
    """Return minimal editable loop syntax."""
    return f"{{for {loop.item} in {loop.collection}}}\n\n{{endfor}}"


def _render_lines(lines, index, context, collections, *, stop_at_end):
    output: list[str] = []
    while index < len(lines):
        line = lines[index]
        if _END_PATTERN.match(line):
            if not stop_at_end:
                raise ValueError("Unexpected {endfor}")
            return output, index + 1

        match = _FOR_PATTERN.match(line)
        if match is None:
            output.append(_format_line(line, context))
            index += 1
            continue

        body, next_index = _collect_loop_body(lines, index + 1)
        collection = match.group("collection")
        item_name = match.group("item")
        for row in collections.get(collection, ()):
            child = TemplateContext(context)
            child[item_name] = TemplateObject(dict(row))
            rendered, consumed = _render_lines(
                body, 0, child, collections, stop_at_end=False
            )
            if consumed != len(body):
                raise ValueError("Invalid nested loop body")
            output.extend(rendered)
        index = next_index

    if stop_at_end:
        raise ValueError("Missing {endfor}")
    return output, index


def _collect_loop_body(lines: list[str], index: int) -> tuple[list[str], int]:
    depth = 1
    body: list[str] = []
    while index < len(lines):
        line = lines[index]
        if _FOR_PATTERN.match(line):
            depth += 1
        elif _END_PATTERN.match(line):
            depth -= 1
            if depth == 0:
                return body, index + 1
        body.append(line)
        index += 1
    raise ValueError("Missing {endfor}")


def _format_line(line: str, context: TemplateContext) -> str:
    try:
        return line.format_map(context)
    except (AttributeError, KeyError, ValueError):
        return line
