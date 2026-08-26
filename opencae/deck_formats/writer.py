"""Capture semantic solver commands and render them through a deck profile."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from .profile import DeckProfile, DeckRecordProfile
from .template_language import render_runtime_template

_PLACEHOLDER = re.compile(r"\{([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)\}")
_FOR = re.compile(r"^\s*\{for\s+([A-Za-z_]\w*)\s+in\s+([A-Za-z_]\w*)\}\s*$")
_END = re.compile(r"^\s*\{endfor\}\s*$")


@dataclass(frozen=True)
class CapturedCommand:
    """One fully lowered native command before textual formatting."""

    name: str
    data: tuple[tuple[object, ...], ...]
    flags: tuple[str, ...]
    keywords: dict[str, object]
    index: int
    record_key: str = ""
    ambient: dict[str, object] = field(default_factory=dict)


@dataclass
class _Unit:
    """One independently orderable semantic output unit."""

    commands: list[tuple[CapturedCommand, str, DeckRecordProfile | None]]
    index: int

    @property
    def key(self) -> str:
        for _command, key, _profile in self.commands:
            if key:
                return key
        return ""


class ProfileCommandWriter:
    """Deck writer that applies templates, enable state, float format and ordering."""

    def __init__(self, profile: DeckProfile):
        if profile.format_name != "FEMaster":
            raise ValueError(
                f"Profile {profile.name!r} is for {profile.format_name}, not FEMaster"
            )
        self.profile = profile
        self._commands: list[CapturedCommand] = []
        self._comments: list[tuple[int, str]] = []
        self._raw_lines: list[tuple[int, str]] = []
        self._index = 0
        self._ambient: dict[str, object] = {}
        self._parents, self._positions = _order_maps(profile.order)

    def command(
        self,
        name: str,
        data=(),
        *,
        flags=(),
        keywords=None,
        record_key: str = "",
    ) -> None:
        """Capture one semantic native command instead of formatting it immediately."""
        upper = str(name).upper()
        normalized_keywords = {
            str(key).upper(): value for key, value in dict(keywords or {}).items()
        }
        ambient = dict(self._ambient)
        if upper == "MATERIAL" and "NAME" in normalized_keywords:
            ambient["material_name"] = normalized_keywords["NAME"]
            self._ambient["material_name"] = normalized_keywords["NAME"]
        elif upper in {"PROFILE", "SECTION", "FIELD", "LOADCASE"}:
            # Material context must not leak into unrelated records.
            self._ambient.pop("material_name", None)
        self._commands.append(
            CapturedCommand(
                upper,
                tuple(_row_tuple(row) for row in data),
                tuple(str(flag) for flag in flags),
                normalized_keywords,
                self._next_index(),
                str(record_key or ""),
                ambient,
            )
        )

    def line(self, text: object = "") -> None:
        """Retain a raw line for rare emitters that do not use semantic commands."""
        self._raw_lines.append((self._next_index(), str(text)))

    def comment(self, text: object) -> None:
        """Capture a formatter-generated comment."""
        self._comments.append((self._next_index(), str(text)))

    def text(self) -> str:
        """Render the complete captured deck using the active profile."""
        matched = [self._matched(command) for command in self._commands]
        units = _semantic_units(matched)
        units.sort(key=lambda unit: (self._rank(unit.key), unit.index))

        blocks: list[str] = []
        for unit in units:
            commands = list(unit.commands)
            if unit.key.startswith("materials.") or unit.key.startswith("analysis."):
                commands.sort(
                    key=lambda item: (
                        self._rank(item[1]),
                        item[0].index,
                    )
                )
            for command, key, record in commands:
                if record is not None and not record.enabled:
                    continue
                rendered = (
                    self._render_profile_record(command, record)
                    if record is not None
                    else _native_command(command)
                )
                rendered = self._apply_block_style(rendered)
                if rendered.strip():
                    blocks.append(rendered.rstrip())

        settings = self.profile.settings
        if bool(settings.get("comments", True)):
            comments = [self._format_comment(text) for _index, text in self._comments]
            if not bool(settings.get("heading", True)):
                comments = [
                    item for item in comments if "OpenCAE Studio generated" not in item
                ]
            blocks = comments + blocks
        if self._raw_lines:
            blocks.extend(text for _index, text in sorted(self._raw_lines))

        separator = "\n\n" if bool(settings.get("blank_lines", True)) else "\n"
        text = separator.join(block for block in blocks if block != "")
        if bool(settings.get("final_newline", True)):
            text += "\n"
        endings = str(settings.get("line_endings", "Platform default"))
        if endings == "CRLF":
            text = text.replace("\r\n", "\n").replace("\n", "\r\n")
        elif endings == "Platform default" and os.linesep != "\n":
            text = text.replace("\r\n", "\n").replace("\n", os.linesep)
        return text

    def _matched(
        self, command: CapturedCommand
    ) -> tuple[CapturedCommand, str, DeckRecordProfile | None]:
        """Resolve the most specific profile record for one native command."""
        if command.record_key:
            record = self.profile.record(command.record_key)
            if record is not None:
                return command, command.record_key, record

        candidates: list[tuple[int, str, DeckRecordProfile]] = []
        for key, record in self.profile.records.items():
            commands = record.commands or (_template_command(record.binding_template),)
            if command.name not in commands:
                continue
            score = _match_score(record.binding_template, command)
            if score is not None:
                candidates.append((score, key, record))
        if not candidates:
            return command, "", None
        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        _score, key, record = candidates[0]
        return command, key, record

    def _render_profile_record(
        self, command: CapturedCommand, record: DeckRecordProfile
    ) -> str:
        values, collections = _bind_command(record.binding_template, command)
        for key, value in command.ambient.items():
            values.setdefault(key, value)
        float_format = record.float_format or str(
            self.profile.settings.get("float_format", ".6g")
        )
        formatted_values = {
            key: _format_value(value, float_format) for key, value in values.items()
        }
        formatted_collections = {
            name: [
                {key: _format_value(value, float_format) for key, value in row.items()}
                for row in rows
            ]
            for name, rows in collections.items()
        }
        return render_runtime_template(
            record.template,
            formatted_values,
            formatted_collections,
        )

    def _rank(self, key: str) -> tuple[int, ...]:
        if not key:
            return (10_000,)
        ranks: list[int] = []
        current = key
        visited: set[str] = set()
        while current in self._parents and current not in visited:
            visited.add(current)
            parent = self._parents[current]
            ranks.append(self._positions.get((parent, current), 10_000))
            current = parent
        if current != "__root__":
            ranks.append(10_000)
        return tuple(reversed(ranks))

    def _apply_block_style(self, block: str) -> str:
        """Apply safe file-wide formatting that does not alter template values."""
        settings = self.profile.settings
        prefix = str(settings.get("prefix", "*"))
        option_separator = str(settings.get("separator", ", "))
        indentation = max(0, int(settings.get("indentation", 0) or 0))
        uppercase = bool(settings.get("uppercase", True))
        result: list[str] = []
        for line in block.splitlines():
            if line.startswith("*"):
                line = prefix + line[1:]
                if option_separator != ", ":
                    line = line.replace(", ", option_separator)
                if uppercase:
                    line = _uppercase_keyword_syntax(line, prefix)
            elif indentation and line.strip():
                line = " " * indentation + line
            result.append(line)
        return "\n".join(result)

    def _format_comment(self, text: str) -> str:
        style = str(self.profile.settings.get("comment_style", "** comment"))
        if style.startswith("#"):
            return f"# {text}"
        if style.startswith("/*"):
            return f"/* {text} */"
        return f"** {text}"

    def _next_index(self) -> int:
        value = self._index
        self._index += 1
        return value


def _semantic_units(
    matched: list[tuple[CapturedCommand, str, DeckRecordProfile | None]],
) -> list[_Unit]:
    """Group owner-sensitive command sequences before applying profile ordering."""
    units: list[_Unit] = []
    index = 0
    while index < len(matched):
        command, key, record = matched[index]
        if key == "materials.header":
            group = [(command, key, record)]
            cursor = index + 1
            while cursor < len(matched):
                candidate = matched[cursor]
                if candidate[1] == "materials.header" or not candidate[1].startswith("materials."):
                    break
                group.append(candidate)
                cursor += 1
            units.append(_Unit(group, command.index))
            index = cursor
            continue
        if key.startswith("analysis.loadcases."):
            group = [(command, key, record)]
            cursor = index + 1
            while cursor < len(matched):
                candidate = matched[cursor]
                group.append(candidate)
                cursor += 1
                if candidate[1] == "analysis.end":
                    break
            units.append(_Unit(group, command.index))
            index = cursor
            continue
        units.append(_Unit([(command, key, record)], command.index))
        index += 1
    return units


def _order_maps(order: dict[str, tuple[str, ...]]):
    parents: dict[str, str] = {}
    positions: dict[tuple[str, str], int] = {}
    for parent, children in order.items():
        for index, child in enumerate(children):
            parents[child] = parent
            positions[(parent, child)] = index
    return parents, positions


def _template_command(template: str) -> str:
    line = next((line.strip() for line in template.splitlines() if line.strip().startswith("*")), "")
    return line[1:].split(",", 1)[0].strip().upper() if line else ""


def _keyword_parts(template: str):
    line = next((line.strip() for line in template.splitlines() if line.strip().startswith("*")), "")
    return [part.strip() for part in line.split(",")] if line else []


def _match_score(template: str, command: CapturedCommand) -> int | None:
    parts = _keyword_parts(template)
    if not parts or parts[0][1:].strip().upper() != command.name:
        return None
    score = 1
    normalized_flags = {_normalize_token(item) for item in command.flags}
    for part in parts[1:]:
        if not part:
            continue
        if "=" in part:
            option, value = (item.strip() for item in part.split("=", 1))
            option = option.upper()
            placeholders = _PLACEHOLDER.findall(value)
            if placeholders:
                if option in command.keywords:
                    score += 3
                continue
            if option in command.keywords:
                if _normalize_token(command.keywords[option]) != _normalize_token(value):
                    return None
                score += 25
            continue
        placeholders = _PLACEHOLDER.findall(part)
        if placeholders:
            score += 1
            continue
        if _normalize_token(part) not in normalized_flags:
            return None
        score += 25
    return score


def _bind_command(template: str, command: CapturedCommand):
    values: dict[str, object] = {}
    collections: dict[str, list[dict[str, object]]] = {}
    parts = _keyword_parts(template)
    flag_index = 0
    for part in parts[1:]:
        if "=" in part:
            option, value = (item.strip() for item in part.split("=", 1))
            placeholders = _PLACEHOLDER.findall(value)
            if placeholders and option.upper() in command.keywords:
                for name in placeholders:
                    if "." not in name:
                        values[name] = command.keywords[option.upper()]
        else:
            placeholders = _PLACEHOLDER.findall(part)
            for name in placeholders:
                if "." not in name and flag_index < len(command.flags):
                    values[name] = command.flags[flag_index]
                    flag_index += 1

    lines = template.splitlines()
    loop_ranges = _loop_ranges(lines)
    used_rows = False
    for start, end, item, collection in loop_ranges:
        field_names = _loop_field_names(lines[start + 1 : end], item)
        if not field_names:
            continue
        collections[collection] = [
            _bind_row(field_names, row) for row in command.data
        ]
        used_rows = True

    if command.data and not used_rows:
        outside = _outside_data_placeholders(lines, loop_ranges)
        flat_values = [value for row in command.data for value in row]
        if outside:
            bound = _bind_row(outside, tuple(flat_values))
            values.update(bound)
    return values, collections


def _loop_ranges(lines: list[str]):
    stack: list[tuple[int, str, str]] = []
    result: list[tuple[int, int, str, str]] = []
    for index, line in enumerate(lines):
        match = _FOR.match(line)
        if match:
            stack.append((index, match.group(1), match.group(2)))
        elif _END.match(line) and stack:
            start, item, collection = stack.pop()
            result.append((start, index, item, collection))
    return result


def _loop_field_names(lines: list[str], item: str) -> list[str]:
    result: list[str] = []
    prefix = item + "."
    for line in lines:
        for name in _PLACEHOLDER.findall(line):
            if name.startswith(prefix):
                field = name[len(prefix) :]
                if field not in result:
                    result.append(field)
    return result


def _outside_data_placeholders(lines, loop_ranges) -> list[str]:
    hidden = set()
    for start, end, _item, _collection in loop_ranges:
        hidden.update(range(start, end + 1))
    result: list[str] = []
    keyword_seen = False
    for index, line in enumerate(lines):
        if index in hidden:
            continue
        if line.strip().startswith("*") and not keyword_seen:
            keyword_seen = True
            continue
        for name in _PLACEHOLDER.findall(line):
            if "." not in name and name not in result:
                result.append(name)
    return result


def _bind_row(names: list[str], row: tuple[object, ...]) -> dict[str, object]:
    if not names:
        return {}
    if len(names) == 1:
        return {names[0]: row[0] if len(row) == 1 else tuple(row)}
    result: dict[str, object] = {}
    for index, name in enumerate(names):
        if index >= len(row):
            result[name] = ""
        elif index == len(names) - 1 and len(row) > len(names):
            result[name] = tuple(row[index:])
        else:
            result[name] = row[index]
    return result


def _row_tuple(row) -> tuple[object, ...]:
    if isinstance(row, str):
        return (row,)
    if isinstance(row, (list, tuple)):
        return tuple(row)
    return (row,)


def _format_value(value: object, float_format: str) -> str:
    if isinstance(value, bool):
        return "ON" if value else "OFF"
    if value is None:
        return "NAN"
    if isinstance(value, float):
        return format(value, float_format)
    if isinstance(value, (list, tuple)):
        return ", ".join(_format_value(item, float_format) for item in value)
    return str(value)


def _native_command(command: CapturedCommand) -> str:
    from opencae.solvers.femaster_dsl.command import format_row, format_value

    options = [str(flag).upper() for flag in command.flags if str(flag).strip()]
    options.extend(
        f"{key.upper()}={format_value(value)}"
        for key, value in command.keywords.items()
        if value not in (None, "")
    )
    lines = ["*" + command.name + (", " + ", ".join(options) if options else "")]
    lines.extend(format_row(row) for row in command.data)
    return "\n".join(lines)


def _normalize_token(value: object) -> str:
    return re.sub(r"[\s_\-]", "", str(value)).upper()


def _uppercase_keyword_syntax(line: str, prefix: str) -> str:
    """Uppercase command/option names without uppercasing user-provided values."""
    body = line[len(prefix) :] if prefix and line.startswith(prefix) else line
    parts = body.split(",")
    if not parts:
        return line
    output = [parts[0].upper()]
    for part in parts[1:]:
        if "=" in part:
            left, right = part.split("=", 1)
            output.append(left.upper() + "=" + right)
        else:
            output.append(part.upper())
    return prefix + ",".join(output)
