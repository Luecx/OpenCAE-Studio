"""Render the small declarative template language used by deck profiles."""

from __future__ import annotations

import re
from dataclasses import dataclass


_FOR_PATTERN = re.compile(
    r"^\s*\{for\s+(?P<item>[A-Za-z_]\w*)\s+in\s+(?P<collection>[A-Za-z_]\w*)\}\s*$"
)
_END_PATTERN = re.compile(r"^\s*\{endfor\}\s*$")


@dataclass(frozen=True)
class TemplateLoop:
    """Provide preview data for one named template collection."""

    collection: str
    item: str
    description: str
    fields: tuple[tuple[str, str, str], ...]
    examples: tuple[dict[str, str], ...]


class _TemplateObject:
    """Expose mapping values through dotted template placeholders."""

    def __init__(self, values: dict[str, object]):
        self._values = values

    def __getattr__(self, name: str):
        return self._values.get(name, "…")


class _TemplateContext(dict):
    """Return an ellipsis for unresolved in-progress placeholders."""

    def __missing__(self, _key):
        return "…"


def render_template(
    template: str,
    values: dict[str, object],
    loops: tuple[TemplateLoop, ...] = (),
) -> str:
    """Render placeholders and ``{for item in collection}`` loop blocks."""
    context = _TemplateContext(values)
    loop_map = {loop.collection: loop for loop in loops}
    lines = template.splitlines()
    try:
        rendered, index = _render_lines(lines, 0, context, loop_map, stop_at_end=False)
    except ValueError:
        return template
    if index != len(lines):
        return template
    return "\n".join(rendered)


def loop_from_spec(spec: dict) -> TemplateLoop:
    """Convert one declarative catalog loop into a typed preview definition."""
    return TemplateLoop(
        collection=str(spec["collection"]),
        item=str(spec["item"]),
        description=str(spec.get("description", "")),
        fields=tuple(spec.get("fields", ())),
        examples=tuple(spec.get("examples", ())),
    )


def loop_skeleton(loop: TemplateLoop) -> str:
    """Return the minimal editable syntax for one loop collection."""
    return f"{{for {loop.item} in {loop.collection}}}\n\n{{endfor}}"


def _render_lines(lines, index, context, loop_map, *, stop_at_end):
    """Render one line range recursively until EOF or the matching end marker."""
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
        loop = loop_map.get(collection)
        if loop is None:
            index = next_index
            continue

        for example in loop.examples:
            child = _TemplateContext(context)
            child[item_name] = _TemplateObject(dict(example))
            rendered, consumed = _render_lines(
                body,
                0,
                child,
                loop_map,
                stop_at_end=False,
            )
            if consumed != len(body):
                raise ValueError("Invalid nested loop body")
            output.extend(rendered)
        index = next_index

    if stop_at_end:
        raise ValueError("Missing {endfor}")
    return output, index


def _collect_loop_body(lines: list[str], index: int) -> tuple[list[str], int]:
    """Collect a loop body while respecting nested loop markers."""
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


def _format_line(line: str, context: _TemplateContext) -> str:
    """Format one normal template line without making partial edits fatal."""
    try:
        return line.format_map(context)
    except (AttributeError, KeyError, ValueError):
        return line
