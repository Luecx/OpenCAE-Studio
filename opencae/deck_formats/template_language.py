"""Render the deliberately small declarative deck-template language."""

from __future__ import annotations

import re
from dataclasses import dataclass


_FOR_PATTERN = re.compile(
    r"^\s*\{for\s+(?P<item>[A-Za-z_]\w*)\s+in\s+(?P<collection>[A-Za-z_]\w*)\}\s*$"
)
_END_PATTERN = re.compile(r"^\s*\{endfor\}\s*$")
_IF_PATTERN = re.compile(r"^\s*\{if\s+(?P<expression>.+?)\}\s*$")
_ELIF_PATTERN = re.compile(r"^\s*\{elif\s+(?P<expression>.+?)\}\s*$")
_ELSE_PATTERN = re.compile(r"^\s*\{else\}\s*$")
_ENDIF_PATTERN = re.compile(r"^\s*\{endif\}\s*$")
_COMPARISON_PATTERN = re.compile(
    r"^(?P<left>.+?)\s+(?P<operator>is not|is|==|!=|>=|<=|>|<)\s+(?P<right>.+?)$"
)


@dataclass(frozen=True)
class TemplateLoop:
    """Preview description for one named template collection."""

    collection: str
    item: str
    description: str
    fields: tuple[tuple[str, str, str], ...]
    examples: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class TemplateValue:
    """Keep one raw semantic value while exposing its formatted deck text."""

    raw: object
    text: str

    def __str__(self) -> str:
        return self.text

    def __format__(self, _spec: str) -> str:
        return self.text


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
        if _ENDIF_PATTERN.match(line) or _ELSE_PATTERN.match(line) or _ELIF_PATTERN.match(line):
            raise ValueError("Unexpected conditional terminator")

        condition = _IF_PATTERN.match(line)
        if condition is not None:
            branches, next_index = _collect_if_branches(
                lines,
                index + 1,
                condition.group("expression"),
            )
            selected = next(
                (
                    body
                    for expression, body in branches
                    if expression is None or _evaluate_expression(expression, context)
                ),
                (),
            )
            rendered, consumed = _render_lines(
                list(selected), 0, context, collections, stop_at_end=False
            )
            if consumed != len(selected):
                raise ValueError("Invalid conditional body")
            output.extend(rendered)
            index = next_index
            continue

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


def _collect_if_branches(
    lines: list[str],
    index: int,
    first_expression: str,
) -> tuple[list[tuple[str | None, tuple[str, ...]]], int]:
    """Collect one if/elif/else block while preserving nested structures."""
    depth = 1
    expression: str | None = first_expression
    body: list[str] = []
    branches: list[tuple[str | None, tuple[str, ...]]] = []
    while index < len(lines):
        line = lines[index]
        if _IF_PATTERN.match(line):
            depth += 1
        elif _ENDIF_PATTERN.match(line):
            depth -= 1
            if depth == 0:
                branches.append((expression, tuple(body)))
                return branches, index + 1
        elif depth == 1:
            match = _ELIF_PATTERN.match(line)
            if match is not None:
                if expression is None:
                    raise ValueError("{elif} cannot follow {else}")
                branches.append((expression, tuple(body)))
                expression = match.group("expression")
                body = []
                index += 1
                continue
            if _ELSE_PATTERN.match(line):
                if expression is None:
                    raise ValueError("Duplicate {else}")
                branches.append((expression, tuple(body)))
                expression = None
                body = []
                index += 1
                continue
        body.append(line)
        index += 1
    raise ValueError("Missing {endif}")


def _evaluate_expression(expression: str, context: TemplateContext) -> bool:
    """Evaluate a small safe boolean expression without Python ``eval``."""
    text = expression.strip()
    or_parts = _split_boolean(text, "or")
    if len(or_parts) > 1:
        return any(_evaluate_expression(part, context) for part in or_parts)
    and_parts = _split_boolean(text, "and")
    if len(and_parts) > 1:
        return all(_evaluate_expression(part, context) for part in and_parts)
    if text.startswith("not "):
        return not _evaluate_expression(text[4:], context)

    match = _COMPARISON_PATTERN.match(text)
    if match is None:
        return bool(_raw_value(_resolve_value(text, context)))

    left = _raw_value(_resolve_value(match.group("left"), context))
    right = _raw_value(_resolve_value(match.group("right"), context))
    operator = match.group("operator")
    if operator == "is":
        return left is right
    if operator == "is not":
        return left is not right
    if operator == "==":
        return left == right
    if operator == "!=":
        return left != right
    try:
        if operator == ">=":
            return left >= right
        if operator == "<=":
            return left <= right
        if operator == ">":
            return left > right
        if operator == "<":
            return left < right
    except TypeError:
        return False
    raise ValueError(f"Unsupported template operator: {operator}")


def _split_boolean(expression: str, operator: str) -> list[str]:
    """Split a simple boolean expression outside quoted string literals."""
    token = f" {operator} "
    quote: str | None = None
    start = 0
    parts: list[str] = []
    index = 0
    while index <= len(expression) - len(token):
        char = expression[index]
        if char in {"'", '"'}:
            quote = None if quote == char else char if quote is None else quote
            index += 1
            continue
        if quote is None and expression[index : index + len(token)] == token:
            parts.append(expression[start:index].strip())
            start = index + len(token)
            index = start
            continue
        index += 1
    if parts:
        parts.append(expression[start:].strip())
        return parts
    return [expression]


def _resolve_value(token: str, context: TemplateContext):
    """Resolve literals and dotted context references used by conditions."""
    text = token.strip()
    lowered = text.casefold()
    if lowered in {"none", "null"}:
        return None
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if (len(text) >= 2) and text[0] == text[-1] and text[0] in {"'", '"'}:
        return text[1:-1]
    try:
        return float(text) if any(char in text for char in ".eE") else int(text)
    except ValueError:
        pass

    parts = text.split(".")
    value = context[parts[0]]
    for name in parts[1:]:
        if isinstance(value, dict):
            value = value.get(name, "")
        else:
            value = getattr(value, name, "")
    return value


def _raw_value(value: object) -> object:
    """Return semantic content from a formatted template value."""
    return value.raw if isinstance(value, TemplateValue) else value


def _format_line(line: str, context: TemplateContext) -> str:
    try:
        return line.format_map(context)
    except (AttributeError, KeyError, ValueError):
        return line
