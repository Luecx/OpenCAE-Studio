"""Parse Abaqus/CalculiX-style INP decks without silently losing unsupported data.

The importer deliberately separates syntax parsing from OpenCAE semantic support.
Keyword spelling, case, whitespace and option order are normalized by the parser;
blocks whose semantics are not implemented are retained in an explicit import
report instead of being ignored.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from collections import OrderedDict
import re

import numpy as np

from .snapshots import MeshBlock, MeshSnapshot


# gmsh type, OpenCAE topology, interpolation order, primary corner count, dimension
ELEMENT_TYPES = {
    "T3": (1, "Lines", 1, 2, 1),
    "B31": (1, "Lines", 1, 2, 1),
    "B32": (8, "Lines", 2, 2, 1),
    "B33": (1, "Lines", 1, 2, 1),
    "T2D2": (1, "Lines", 1, 2, 1),
    "T2D3": (8, "Lines", 2, 2, 1),
    "T3D2": (1, "Lines", 1, 2, 1),
    "T3D3": (8, "Lines", 2, 2, 1),
    "S3": (2, "Triangles", 1, 3, 2),
    "STRI3": (2, "Triangles", 1, 3, 2),
    "MITC3FRT": (2, "Triangles", 1, 3, 2),
    "S4": (3, "Quadrilaterals", 1, 4, 2),
    "S4R": (3, "Quadrilaterals", 1, 4, 2),
    "MITC4": (3, "Quadrilaterals", 1, 4, 2),
    "MITC4FRT": (3, "Quadrilaterals", 1, 4, 2),
    "QSPT": (3, "Quadrilaterals", 1, 4, 2),
    "S6": (9, "Triangles", 2, 3, 2),
    "MITC6FRT": (9, "Triangles", 2, 3, 2),
    "S8": (16, "Quadrilaterals", 2, 4, 2),
    "S8R": (16, "Quadrilaterals", 2, 4, 2),
    "MITC8": (16, "Quadrilaterals", 2, 4, 2),
    "MITC8FRT": (16, "Quadrilaterals", 2, 4, 2),
    "C3D4": (4, "Tetrahedra", 1, 4, 3),
    "C3D5": (7, "Pyramids", 1, 5, 3),
    "C3D6": (6, "Pentahedra", 1, 6, 3),
    "C3D8": (5, "Hexahedra", 1, 8, 3),
    "C3D8R": (5, "Hexahedra", 1, 8, 3),
    "C3D10": (11, "Tetrahedra", 2, 4, 3),
    "C3D13": (19, "Pyramids", 2, 5, 3),
    "C3D15": (18, "Pentahedra", 2, 6, 3),
    "C3D20": (17, "Hexahedra", 2, 8, 3),
    "C3D20R": (17, "Hexahedra", 2, 8, 3),
}

CONNECTIVITY_COUNT = {
    "T3": 2, "B31": 2, "B32": 3, "B33": 2, "T2D2": 2, "T2D3": 3,
    "T3D2": 2, "T3D3": 3,
    "S3": 3, "STRI3": 3, "MITC3FRT": 3,
    "S4": 4, "S4R": 4, "MITC4": 4, "MITC4FRT": 4, "QSPT": 4,
    "S6": 6, "MITC6FRT": 6, "S8": 8, "S8R": 8,
    "MITC8": 8, "MITC8FRT": 8,
    "C3D4": 4, "C3D5": 5, "C3D6": 6, "C3D8": 8, "C3D8R": 8,
    "C3D10": 10, "C3D13": 13, "C3D15": 15, "C3D20": 20, "C3D20R": 20,
}

_SUPPORTED_KEYWORDS = frozenset({"NODE", "ELEMENT", "NSET", "ELSET", "SURFACE"})


@dataclass(frozen=True, slots=True)
class InpBlock:
    """One parsed keyword block with normalized syntax and source location."""

    keyword: str
    options: tuple[tuple[str, str | bool], ...]
    data: tuple[tuple[int, str], ...]
    line_number: int
    header: str

    def option(self, key: str, default=None):
        key = _canonical(key)
        return dict(self.options).get(key, default)

    def has_flag(self, key: str) -> bool:
        return self.option(key, False) is True


@dataclass(frozen=True, slots=True)
class InpSkippedKeyword:
    """A keyword block that was parsed but not semantically imported."""

    keyword: str
    line_number: int
    detail: str = ""
    reason: str = "Not supported by the INP importer"

    @property
    def label(self) -> str:
        suffix = f" ({self.detail})" if self.detail else ""
        return f"*{self.keyword}{suffix}"


@dataclass(slots=True)
class InpImportReport:
    """Describe exactly what the importer accepted, skipped, or could not resolve."""

    imported_keywords: list[str] = field(default_factory=list)
    skipped: list[InpSkippedKeyword] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def mark_imported(self, keyword: str) -> None:
        keyword = _canonical(keyword)
        if keyword not in self.imported_keywords:
            self.imported_keywords.append(keyword)

    @property
    def unsupported_keywords(self) -> tuple[str, ...]:
        result = []
        for item in self.skipped:
            if item.label not in result:
                result.append(item.label)
        return tuple(result)

    def format_unimported(self) -> str:
        """Return a concrete, line-numbered list suitable for the import dialog."""
        if not self.skipped:
            return ""
        grouped: OrderedDict[tuple[str, str, str], list[int]] = OrderedDict()
        for item in self.skipped:
            key = (item.label, item.reason, item.detail)
            grouped.setdefault(key, []).append(int(item.line_number))
        lines = []
        for (label, reason, _detail), numbers in grouped.items():
            locations = ", ".join(str(value) for value in numbers)
            noun = "line" if len(numbers) == 1 else "lines"
            lines.append(f"{label} — {noun} {locations}: {reason}")
        return "\n".join(lines)


@dataclass(slots=True)
class InpMeshImportResult:
    """Mesh plus named mesh regions recovered from one keyword deck."""

    snapshot: MeshSnapshot
    node_sets: dict[str, tuple[int, ...]] = field(default_factory=dict)
    element_sets: dict[str, tuple[int, ...]] = field(default_factory=dict)
    surfaces: dict[str, tuple[tuple[int, str], ...]] = field(default_factory=dict)
    report: InpImportReport = field(default_factory=InpImportReport)


def parse_inp(text: str) -> tuple[InpBlock, ...]:
    """Parse INP keyword/data blocks independent of capitalization and spacing."""
    blocks: list[InpBlock] = []
    keyword = None
    options = ()
    data: list[tuple[int, str]] = []
    line_number = 0
    header = ""

    def flush():
        nonlocal keyword, options, data, line_number, header
        if keyword is not None:
            blocks.append(InpBlock(keyword, options, tuple(data), line_number, header))
        keyword = None
        options = ()
        data = []
        line_number = 0
        header = ""

    for number, raw in enumerate(str(text).splitlines(), 1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("**"):
            continue
        if stripped.startswith("*"):
            flush()
            keyword, options = _parse_header(stripped)
            line_number = number
            header = stripped
            continue
        if keyword is not None:
            data.append((number, stripped))
    flush()
    return tuple(blocks)


def read_inp(path, part_id: str) -> InpMeshImportResult:
    """Read supported mesh/region semantics and report every unsupported keyword."""
    path = Path(path)
    blocks = parse_inp(path.read_text(errors="replace"))
    report = InpImportReport()
    nodes: dict[int, tuple[float, float, float]] = {}
    element_rows: OrderedDict[str, list[tuple[int, tuple[int, ...]]]] = OrderedDict()
    node_sets: OrderedDict[str, set[int]] = OrderedDict()
    element_sets: OrderedDict[str, set[int]] = OrderedDict()
    surface_specs: OrderedDict[str, list[tuple[str, str]]] = OrderedDict()

    for block in blocks:
        if block.keyword not in _SUPPORTED_KEYWORDS:
            report.skipped.append(
                InpSkippedKeyword(block.keyword, block.line_number)
            )
            continue
        if block.keyword == "NODE":
            _import_nodes(block, nodes, node_sets, report)
        elif block.keyword == "ELEMENT":
            _import_elements(block, element_rows, element_sets, report)
        elif block.keyword == "NSET":
            _import_set(block, node_sets, "NSET", report)
        elif block.keyword == "ELSET":
            _import_set(block, element_sets, "ELSET", report)
        elif block.keyword == "SURFACE":
            _import_surface(block, surface_specs, report)

    if not nodes:
        raise ValueError("INP file contains no supported *NODE data")

    tags = np.asarray(sorted(nodes), dtype=np.int64)
    lookup = {int(tag): index for index, tag in enumerate(tags)}
    blocks_out: list[MeshBlock] = []
    exported_elements: set[int] = set()
    for element_type, rows in element_rows.items():
        spec = ELEMENT_TYPES[element_type]
        gmsh, topology, order, primary, dimension = spec
        valid_rows = []
        ids = []
        for element_id, connectivity in rows:
            missing = [node for node in connectivity if node not in lookup]
            if missing:
                report.warnings.append(
                    f"Element {element_id} ({element_type}) was skipped because nodes "
                    + ", ".join(map(str, missing))
                    + " are missing"
                )
                continue
            valid_rows.append([lookup[node] for node in connectivity])
            ids.append(element_id)
            exported_elements.add(int(element_id))
        if valid_rows:
            blocks_out.append(
                MeshBlock(
                    gmsh,
                    topology,
                    dimension,
                    order,
                    primary,
                    np.asarray(valid_rows, dtype=np.int64),
                    np.asarray(ids, dtype=np.int64),
                )
            )

    if not blocks_out:
        raise ValueError("INP file contains no supported *ELEMENT data")

    dimension = max(block.dimension for block in blocks_out)
    snapshot = MeshSnapshot(
        part_id,
        tags,
        np.asarray([nodes[int(tag)] for tag in tags], dtype=float),
        blocks_out,
        dimension,
        fingerprint=str(path),
    )
    resolved_surfaces = _resolve_surfaces(
        surface_specs,
        element_sets,
        exported_elements,
        report,
    )
    return InpMeshImportResult(
        snapshot=snapshot,
        node_sets={name: tuple(sorted(values)) for name, values in node_sets.items()},
        element_sets={name: tuple(sorted(values & exported_elements)) for name, values in element_sets.items()},
        surfaces=resolved_surfaces,
        report=report,
    )


def _parse_header(line: str):
    tokens = [token.strip() for token in line[1:].split(",")]
    keyword = _canonical(tokens[0])
    options = []
    for token in tokens[1:]:
        if not token:
            continue
        if "=" in token:
            key, value = token.split("=", 1)
            options.append((_canonical(key), value.strip()))
        else:
            options.append((_canonical(token), True))
    return keyword, tuple(options)


def _canonical(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).upper()


def _csv(line: str) -> list[str]:
    return [value.strip() for value in line.split(",")]


def _name_option(block: InpBlock, key: str) -> str:
    value = block.option(key, "")
    return str(value).strip() if value not in (None, True, False) else ""


def _import_nodes(block, nodes, node_sets, report):
    imported = False
    inline_set = _name_option(block, "NSET")
    target = node_sets.setdefault(inline_set, set()) if inline_set else None
    for number, line in block.data:
        values = _csv(line)
        if len(values) < 4:
            report.warnings.append(f"*NODE line {number} was not imported: expected id,x,y,z")
            continue
        try:
            node_id = int(values[0])
            nodes[node_id] = tuple(float(value) for value in values[1:4])
        except ValueError:
            report.warnings.append(f"*NODE line {number} was not imported: invalid numeric data")
            continue
        if target is not None:
            target.add(node_id)
        imported = True
    if imported:
        report.mark_imported("NODE")


def _import_elements(block, element_rows, element_sets, report):
    element_type = _canonical(_name_option(block, "TYPE") or "C3D4")
    if element_type not in ELEMENT_TYPES:
        report.skipped.append(
            InpSkippedKeyword(
                "ELEMENT",
                block.line_number,
                f"TYPE={element_type}",
                f"Unsupported element type {element_type}",
            )
        )
        return
    expected = CONNECTIVITY_COUNT[element_type]
    rows = element_rows.setdefault(element_type, [])
    inline_set = _name_option(block, "ELSET")
    target = element_sets.setdefault(inline_set, set()) if inline_set else None
    pending: list[str] = []
    pending_line = block.line_number
    for number, line in block.data:
        values = [value for value in _csv(line) if value]
        if not pending:
            pending_line = number
        pending.extend(values)
        while len(pending) >= expected + 1:
            record, pending = pending[: expected + 1], pending[expected + 1 :]
            try:
                element_id = int(record[0])
                connectivity = tuple(int(value) for value in record[1:])
            except ValueError:
                report.warnings.append(
                    f"*ELEMENT line {pending_line} was not imported: invalid integer data"
                )
                continue
            rows.append((element_id, connectivity))
            if target is not None:
                target.add(element_id)
    if pending:
        report.warnings.append(
            f"*ELEMENT line {pending_line} was not imported: incomplete {element_type} connectivity"
        )
    if rows:
        report.mark_imported("ELEMENT")


def _import_set(block, collection, keyword, report):
    name = _name_option(block, keyword)
    if not name:
        report.skipped.append(
            InpSkippedKeyword(keyword, block.line_number, reason=f"*{keyword} has no {keyword}= name")
        )
        return
    target = collection.setdefault(name, set())
    imported = False
    for number, line in block.data:
        values = [value for value in _csv(line) if value]
        try:
            if block.has_flag("GENERATE"):
                if len(values) < 2:
                    raise ValueError
                start, stop = int(values[0]), int(values[1])
                step = int(values[2]) if len(values) > 2 else 1
                if step == 0:
                    raise ValueError
                endpoint = stop + (1 if step > 0 else -1)
                target.update(range(start, endpoint, step))
            else:
                target.update(int(value) for value in values)
        except ValueError:
            report.warnings.append(
                f"*{keyword} line {number} was not imported: only numeric members are supported"
            )
            continue
        imported = True
    if imported:
        report.mark_imported(keyword)


def _import_surface(block, surfaces, report):
    name = _name_option(block, "NAME")
    surface_type = _canonical(_name_option(block, "TYPE") or "ELEMENT")
    if not name:
        report.skipped.append(
            InpSkippedKeyword("SURFACE", block.line_number, reason="*SURFACE has no NAME=")
        )
        return
    if surface_type != "ELEMENT":
        report.skipped.append(
            InpSkippedKeyword(
                "SURFACE",
                block.line_number,
                f"TYPE={surface_type}",
                "Only element-based surfaces are imported",
            )
        )
        return
    rows = surfaces.setdefault(name, [])
    imported = False
    for number, line in block.data:
        values = [value for value in _csv(line) if value]
        if len(values) < 2:
            report.warnings.append(
                f"*SURFACE line {number} was not imported: expected element/ELSET and side"
            )
            continue
        rows.append((values[0].strip(), _canonical(values[1])))
        imported = True
    if imported:
        report.mark_imported("SURFACE")


def _resolve_surfaces(surface_specs, element_sets, exported_elements, report):
    result = {}
    for name, specs in surface_specs.items():
        facets: set[tuple[int, str]] = set()
        for reference, side in specs:
            try:
                element_ids = (int(reference),)
            except ValueError:
                element_ids = tuple(element_sets.get(reference, ()))
                if not element_ids:
                    # Set names are case-insensitive in the deck grammar for our importer.
                    match = next(
                        (values for key, values in element_sets.items() if key.upper() == reference.upper()),
                        None,
                    )
                    element_ids = tuple(match or ())
            if not element_ids:
                report.warnings.append(
                    f"Surface '{name}' reference '{reference}' could not be resolved to an element or ELSET"
                )
                continue
            for element_id in element_ids:
                if int(element_id) in exported_elements:
                    facets.add((int(element_id), side))
        result[name] = tuple(sorted(facets))
    return result
