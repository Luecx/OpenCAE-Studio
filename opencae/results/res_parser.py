"""Parse FEMaster's native text RES result format without mesh assumptions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import numpy as np

_HEADER_VALUE = re.compile(r"([A-Z_]+)=([^,]+)", re.IGNORECASE)
_FRAME_SUFFIX = re.compile(r"^(.*?)[_ ](\d+)$")
_SECTION_FORCE_NAME = "LOCAL_SECTION_FORCES"


@dataclass(frozen=True, slots=True)
class ResFieldBlock:
    name: str
    display_name: str
    block_name: str
    domain: str
    components: tuple[str, ...]
    loadcase: int
    frame_id: int
    frame_value: float
    block_index: int
    values: dict[tuple[str, ...], np.ndarray]


@dataclass(frozen=True, slots=True)
class ResData:
    fields: tuple[ResFieldBlock, ...]


def parse_res(path: str | Path) -> ResData:
    """Return all parseable FEMaster fields grouped by their loadcase."""
    source = Path(path)
    current_loadcase = 1
    block_index = 0
    blocks: list[ResFieldBlock] = []
    lines = source.read_text(errors="replace").splitlines()
    index = 0

    while index < len(lines):
        line = lines[index].strip()
        if line.startswith("LC "):
            try:
                current_loadcase = int(line.split(maxsplit=1)[1])
            except (IndexError, ValueError):
                current_loadcase = max(1, current_loadcase)
            index += 1
            continue
        if not line.startswith("FIELD,"):
            index += 1
            continue

        metadata = {
            key.upper(): value.strip()
            for key, value in _HEADER_VALUE.findall(line)
        }
        raw_name = metadata.get("NAME", f"FIELD_{block_index + 1}")
        domain = metadata.get("TYPE", "UNKNOWN").upper()
        index_cols = int(metadata.get("INDEX_COLS", "0") or 0)
        value_cols = int(
            metadata.get("VALUE_COLS", metadata.get("COLS", "0")) or 0
        )
        declared_rows = int(metadata.get("ROWS", "0") or 0)
        values: dict[tuple[str, ...], np.ndarray] = {}
        dense_row = 0
        index += 1

        while index < len(lines):
            current = lines[index].strip()
            index += 1
            if current == "END FIELD":
                break
            if not current:
                continue
            tokens = current.split()
            if len(tokens) < index_cols + value_cols:
                continue
            row_indices = (
                tuple(tokens[:index_cols]) if index_cols else (str(dense_row),)
            )
            try:
                row_values = np.asarray(
                    [
                        float(value)
                        for value in tokens[index_cols : index_cols + value_cols]
                    ],
                    dtype=float,
                )
            except ValueError:
                continue
            values[row_indices] = row_values
            dense_row += 1

        if declared_rows and dense_row == 0:
            continue

        display_name, frame_id = field_identity(raw_name)
        blocks.append(
            ResFieldBlock(
                name=raw_name,
                display_name=display_name,
                block_name=block_name(raw_name),
                domain=domain,
                components=components(raw_name, value_cols),
                loadcase=current_loadcase,
                frame_id=frame_id,
                # The current text writer does not persist frame_value. Keep a
                # deterministic ordinal until the RES format gains that value.
                frame_value=float(frame_id),
                block_index=block_index,
                values=values,
            )
        )
        block_index += 1

    return ResData(tuple(blocks))


def field_identity(name: str) -> tuple[str, int]:
    """Separate FEMaster's optional numeric frame suffix from a field name."""
    raw = str(name).strip()
    match = _FRAME_SUFFIX.match(raw)
    if match is None:
        return raw, 1
    base = match.group(1)
    number = int(match.group(2))
    normalized = re.sub(r"[^A-Z]", "", base.upper())
    if normalized in {"MODESHAPE", "BUCKLINGMODE", "PARTICIPATION"}:
        return base, max(1, number)
    return base, number + 1


def block_name(name: str) -> str:
    """Use FRD-compatible internal array names without changing RES labels."""
    normalized = re.sub(r"[^A-Z]", "", str(name).upper())
    if normalized.startswith("DISPLACEMENTREAL"):
        return "DISPREAL"
    if normalized.startswith("DISPLACEMENTIMAG"):
        return "DISPIMAG"
    if normalized.startswith(("DISPLACEMENT", "MODESHAPE", "BUCKLINGMODE")):
        return "DISP"
    if normalized.startswith("REACTIONFORCES"):
        return "FORC"
    if normalized.startswith("EXTERNALFORCES"):
        return "EXTFORC"
    if normalized.startswith("INTERNALFORCES"):
        return "INTFORC"
    if normalized.startswith("STRESSREAL"):
        return "STRREAL"
    if normalized.startswith("STRESSIMAG"):
        return "STRIMAG"
    return field_identity(name)[0].upper()


def components(name: str, count: int) -> tuple[str, ...]:
    """Return the component order emitted by current FEMaster result fields."""
    normalized = re.sub(r"[^A-Z]", "", str(name).upper())
    candidates: tuple[str, ...]
    if normalized.startswith(("DISPLACEMENT", "MODESHAPE", "BUCKLINGMODE")):
        candidates = ("D1", "D2", "D3", "D4", "D5", "D6")
    elif normalized.startswith("VELOCITY"):
        candidates = ("V1", "V2", "V3", "V4", "V5", "V6")
    elif normalized.startswith("ACCELERATION"):
        candidates = ("A1", "A2", "A3", "A4", "A5", "A6")
    elif normalized.startswith(
        ("REACTIONFORCES", "EXTERNALFORCES", "INTERNALFORCES")
    ):
        candidates = ("F1", "F2", "F3", "F4", "F5", "F6")
    elif normalized.startswith("STRESS"):
        candidates = ("SXX", "SYY", "SZZ", "SYZ", "SZX", "SXY")
    elif normalized.startswith("STRAIN"):
        candidates = ("EXX", "EYY", "EZZ", "EYZ", "EZX", "EXY")
    elif normalized.startswith("SHELLRESULTANTS"):
        candidates = ("NXX", "NYY", "NXY", "MXX", "MYY", "MXY", "QX", "QY")
    elif normalized == _SECTION_FORCE_NAME.replace("_", ""):
        candidates = ("N", "VY", "VZ", "T", "MY", "MZ")
    else:
        candidates = ()
    result = list(candidates[:count])
    result.extend(f"C{index + 1}" for index in range(len(result), count))
    return tuple(result)


def value_matrix(block: ResFieldBlock) -> np.ndarray:
    if not block.values:
        return np.empty((0, len(block.components)), dtype=float)
    values = np.full(
        (len(block.values), len(block.components)),
        np.nan,
        dtype=float,
    )
    for row, current in enumerate(block.values.values()):
        width = min(values.shape[1], len(current))
        values[row, :width] = current[:width]
    return values


def required_semantic_ids(data: ResData) -> tuple[set[str], set[str]]:
    """Return entity ids required to disambiguate a companion input deck."""
    nodes: set[str] = set()
    elements: set[str] = set()
    for block in data.fields:
        if block.domain == "NODE":
            nodes.update(indices[0] for indices in block.values if indices)
        elif block.domain in {
            "ELEMENT",
            "ELEMENT_NODAL",
            "ELEMENT_IP",
            "ELEMENT_MP",
        }:
            elements.update(indices[0] for indices in block.values if indices)
    return nodes, elements
