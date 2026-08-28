from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

import numpy as np

from .snapshots import MeshBlock, MeshSnapshot


_TYPE = {
    "T3": (1, "Lines", 1, 2, 1), "B33": (1, "Lines", 1, 2, 1),
    "S3": (2, "Triangles", 1, 3, 2), "MITC3FRT": (2, "Triangles", 1, 3, 2),
    "S4": (3, "Quadrilaterals", 1, 4, 2), "MITC4": (3, "Quadrilaterals", 1, 4, 2),
    "MITC4FRT": (3, "Quadrilaterals", 1, 4, 2), "QSPT": (3, "Quadrilaterals", 1, 4, 2),
    "S6": (9, "Triangles", 2, 3, 2), "MITC6FRT": (9, "Triangles", 2, 3, 2),
    "S8": (16, "Quadrilaterals", 2, 4, 2), "MITC8": (16, "Quadrilaterals", 2, 4, 2),
    "MITC8FRT": (16, "Quadrilaterals", 2, 4, 2),
    "C3D4": (4, "Tetrahedra", 1, 4, 3), "C3D5": (7, "Pyramids", 1, 5, 3),
    "C3D6": (6, "Pentahedra", 1, 6, 3), "C3D8": (5, "Hexahedra", 1, 8, 3), "C3D8R": (5, "Hexahedra", 1, 8, 3),
    "C3D10": (11, "Tetrahedra", 2, 4, 3), "C3D13": (19, "Pyramids", 2, 5, 3),
    "C3D15": (18, "Pentahedra", 2, 6, 3), "C3D20": (17, "Hexahedra", 2, 8, 3), "C3D20R": (17, "Hexahedra", 2, 8, 3),
}

# Native deck codes emitted by OpenCAE that map back to one canonical internal
# element definition.  This makes import an actual inverse of our Abaqus /
# CalculiX element lowering rather than only accepting FEMaster spellings.
_ELEMENT_TYPE_ALIASES = {
    "T3D2": "T3",
    "B31": "B33",
    "STRI65": "S6",
    "S8R": "S8",
}

_NODES_PER_ELEMENT = {
    "T3": 2, "B33": 2,
    "S3": 3, "MITC3FRT": 3,
    "S4": 4, "MITC4": 4, "MITC4FRT": 4, "QSPT": 4,
    "S6": 6, "MITC6FRT": 6,
    "S8": 8, "MITC8": 8, "MITC8FRT": 8,
    "C3D4": 4, "C3D5": 5, "C3D6": 6, "C3D8": 8, "C3D8R": 8,
    "C3D10": 10, "C3D13": 13, "C3D15": 15, "C3D20": 20, "C3D20R": 20,
}


@dataclass(frozen=True, slots=True)
class KeywordImportIssue:
    """One keyword block that could not be represented by the mesh importer."""

    keyword: str
    line_number: int
    header: str
    reason: str

    def format(self) -> str:
        return f"{self.header} — line {self.line_number}: {self.reason}"


@dataclass(slots=True)
class MeshImportReport:
    """Audit trail for keyword-deck import instead of silently dropped blocks."""

    imported_keywords: list[str] = field(default_factory=list)
    not_imported: list[KeywordImportIssue] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_unimported_keywords(self) -> bool:
        return bool(self.not_imported)

    def mark_imported(self, keyword: str) -> None:
        value = str(keyword).upper().lstrip("*")
        if value not in self.imported_keywords:
            self.imported_keywords.append(value)

    def reject(self, keyword: str, line_number: int, header: str, reason: str) -> None:
        self.not_imported.append(
            KeywordImportIssue(
                keyword=str(keyword).upper().lstrip("*"),
                line_number=int(line_number),
                header=str(header).strip(),
                reason=str(reason),
            )
        )

    def format_unimported(self) -> str:
        if not self.not_imported:
            return "All encountered keyword blocks were imported."
        return "\n".join(issue.format() for issue in self.not_imported)


@dataclass(frozen=True, slots=True)
class MeshImportResult:
    snapshot: MeshSnapshot
    node_sets: dict[str, tuple[int, ...]]
    element_sets: dict[str, tuple[int, ...]]
    surfaces: dict[str, tuple[tuple[int, str], ...]]
    report: MeshImportReport


def read_mesh(path, part_id):
    """Read a mesh and preserve the historical MeshSnapshot-only API."""
    return read_mesh_with_report(path, part_id).snapshot


def read_mesh_with_report(path, part_id) -> MeshImportResult:
    suffix = Path(path).suffix.lower()
    if suffix in {".inp", ".fem"}:
        return _read_keyword_deck(path, part_id)
    snapshot = _read_pyvista(path, part_id)
    return MeshImportResult(snapshot, {}, {}, {}, MeshImportReport())


def _read_keyword_deck(path, part_id) -> MeshImportResult:
    nodes: dict[int, tuple[float, float, float]] = {}
    groups: dict[str, list[tuple[int, tuple[int, ...]]]] = {}
    node_sets: dict[str, list[int | str]] = {}
    element_sets: dict[str, list[int | str]] = {}
    raw_surfaces: dict[str, list[tuple[int | str, str]]] = {}
    report = MeshImportReport()

    current = None
    context = {}
    pending_element: list[int] = []

    lines = Path(path).read_text(errors="replace").splitlines()
    for line_number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("**"):
            continue
        if line.startswith("*"):
            if pending_element:
                report.warnings.append(
                    f"Incomplete element connectivity before line {line_number} was ignored"
                )
                pending_element = []
            keyword, params, flags = _parse_keyword(line)
            current, context = _keyword_context(
                keyword,
                params,
                flags,
                line,
                line_number,
                groups,
                node_sets,
                element_sets,
                raw_surfaces,
                report,
            )
            continue

        values = [item.strip() for item in line.split(",") if item.strip()]
        if current == "node":
            if len(values) < 4:
                report.warnings.append(f"Malformed *NODE data at line {line_number}: {line}")
                continue
            node_id = int(values[0])
            nodes[node_id] = tuple(map(float, values[1:4]))
            set_name = context.get("set_name")
            if set_name:
                node_sets.setdefault(set_name, []).append(node_id)
        elif current == "element":
            pending_element.extend(int(value) for value in values)
            required = 1 + int(context["node_count"])
            if len(pending_element) < required:
                continue
            if len(pending_element) > required:
                report.warnings.append(
                    f"Extra element connectivity values at line {line_number} were ignored"
                )
            element_id = int(pending_element[0])
            connectivity = tuple(int(value) for value in pending_element[1:required])
            element_type = context["element_type"]
            groups[element_type].append((element_id, connectivity))
            set_name = context.get("set_name")
            if set_name:
                element_sets.setdefault(set_name, []).append(element_id)
            pending_element = []
        elif current in {"nset", "elset"}:
            target = node_sets if current == "nset" else element_sets
            name = context["set_name"]
            if context.get("generate"):
                try:
                    target[name].extend(_generated_labels(values))
                except (TypeError, ValueError) as exc:
                    report.warnings.append(
                        f"Invalid GENERATE data for *{current.upper()} at line {line_number}: {exc}"
                    )
            else:
                for value in values:
                    try:
                        target[name].append(int(value))
                    except ValueError:
                        target[name].append(value)
        elif current == "surface":
            if len(values) < 2:
                report.warnings.append(f"Malformed *SURFACE data at line {line_number}: {line}")
                continue
            reference: int | str
            try:
                reference = int(values[0])
            except ValueError:
                reference = values[0]
            raw_surfaces[context["surface_name"]].append(
                (reference, values[1].upper())
            )

    resolved_node_sets = _resolve_sets(node_sets, report, "NSET")
    resolved_element_sets = _resolve_sets(element_sets, report, "ELSET")
    surfaces = _resolve_surfaces(raw_surfaces, resolved_element_sets, report)

    tags = np.asarray(sorted(nodes), np.int64)
    lookup = {tag: index for index, tag in enumerate(tags)}
    blocks = []
    for name, rows in groups.items():
        if not rows:
            continue
        gmsh, topology, order, primary, dimension = _TYPE[name]
        connectivity = []
        element_tags = []
        for element_id, row in rows:
            try:
                connectivity.append([lookup[tag] for tag in row])
            except KeyError as exc:
                raise ValueError(
                    f"Element {element_id} references missing node {int(exc.args[0])}"
                ) from exc
            element_tags.append(element_id)
        blocks.append(
            MeshBlock(
                gmsh,
                name,
                dimension,
                order,
                primary,
                np.asarray(connectivity, np.int64),
                np.asarray(element_tags, np.int64),
            )
        )
    snapshot = MeshSnapshot(
        part_id,
        tags,
        np.asarray([nodes[int(tag)] for tag in tags], dtype=float),
        blocks,
        max((block.dimension for block in blocks), default=0),
        fingerprint=str(path),
    )
    return MeshImportResult(
        snapshot=snapshot,
        node_sets={name: tuple(values) for name, values in resolved_node_sets.items()},
        element_sets={name: tuple(values) for name, values in resolved_element_sets.items()},
        surfaces={name: tuple(values) for name, values in surfaces.items()},
        report=report,
    )


def _keyword_context(
    keyword,
    params,
    flags,
    header,
    line_number,
    groups,
    node_sets,
    element_sets,
    raw_surfaces,
    report,
):
    if keyword == "NODE":
        if "INPUT" in params:
            report.reject(keyword, line_number, header, "external INPUT files are not followed")
            return None, {}
        system = params.get("SYSTEM", "R").upper()
        if system not in {"", "R", "RECTANGULAR"}:
            report.reject(
                keyword,
                line_number,
                header,
                f"coordinate SYSTEM={system} is not supported by orphan-mesh import",
            )
            return None, {}
        _report_partial_parameters(
            keyword, params, flags, {"NSET", "SYSTEM"}, set(), header, line_number, report
        )
        report.mark_imported(keyword)
        return "node", {"set_name": params.get("NSET", "").strip()}

    if keyword == "ELEMENT":
        if "INPUT" in params:
            report.reject(keyword, line_number, header, "external INPUT files are not followed")
            return None, {}
        native_element_type = params.get("TYPE", "").upper()
        if not native_element_type:
            report.reject(keyword, line_number, header, "TYPE is required")
            return None, {}
        element_type = _ELEMENT_TYPE_ALIASES.get(native_element_type, native_element_type)
        if element_type not in _TYPE:
            report.reject(
                keyword,
                line_number,
                header,
                f"element TYPE={native_element_type} is not supported",
            )
            return None, {}
        _report_partial_parameters(
            keyword, params, flags, {"TYPE", "ELSET"}, set(), header, line_number, report
        )
        groups.setdefault(element_type, [])
        report.mark_imported(keyword)
        return "element", {
            "element_type": element_type,
            "node_count": _NODES_PER_ELEMENT[element_type],
            "set_name": params.get("ELSET", "").strip(),
        }

    if keyword in {"NSET", "ELSET"}:
        key = keyword
        name = params.get(key, "").strip()
        if not name:
            report.reject(keyword, line_number, header, f"{key}=name is required")
            return None, {}
        if "INSTANCE" in params:
            report.reject(
                keyword,
                line_number,
                header,
                "assembly INSTANCE-qualified sets are not supported by Part mesh import",
            )
            return None, {}
        allowed_flags = {"GENERATE", "UNSORTED"}
        _report_partial_parameters(
            keyword, params, flags, {key}, allowed_flags, header, line_number, report
        )
        target = node_sets if keyword == "NSET" else element_sets
        target.setdefault(name, [])
        report.mark_imported(keyword)
        return keyword.lower(), {
            "set_name": name,
            "generate": "GENERATE" in flags,
        }

    if keyword == "SURFACE":
        name = params.get("NAME", "").strip()
        surface_type = params.get("TYPE", "ELEMENT").upper()
        if not name:
            report.reject(keyword, line_number, header, "NAME is required")
            return None, {}
        if surface_type != "ELEMENT":
            report.reject(
                keyword,
                line_number,
                header,
                f"only TYPE=ELEMENT surfaces are supported, not TYPE={surface_type}",
            )
            return None, {}
        if "INSTANCE" in params:
            report.reject(
                keyword,
                line_number,
                header,
                "assembly INSTANCE-qualified surfaces are not supported by Part mesh import",
            )
            return None, {}
        _report_partial_parameters(
            keyword,
            params,
            flags,
            {"NAME", "TYPE"},
            set(),
            header,
            line_number,
            report,
        )
        raw_surfaces.setdefault(name, [])
        report.mark_imported(keyword)
        return "surface", {"surface_name": name}

    report.reject(
        keyword,
        line_number,
        header,
        "keyword is not supported by the orphan-mesh importer",
    )
    return None, {}


def _report_partial_parameters(
    keyword,
    params,
    flags,
    allowed_params,
    allowed_flags,
    header,
    line_number,
    report,
):
    extras = sorted(set(params) - set(allowed_params))
    extra_flags = sorted(set(flags) - set(allowed_flags))
    ignored = [*(f"{name}=..." for name in extras), *extra_flags]
    if ignored:
        report.reject(
            keyword,
            line_number,
            header,
            "keyword data were imported, but these options were not: "
            + ", ".join(ignored),
        )


def _parse_keyword(line):
    parts = [part.strip() for part in line[1:].split(",")]
    keyword = parts[0].upper()
    params = {}
    flags = set()
    for part in parts[1:]:
        if not part:
            continue
        if "=" in part:
            key, value = part.split("=", 1)
            params[key.strip().upper()] = value.strip()
        else:
            flags.add(part.upper())
    return keyword, params, flags


def _generated_labels(values):
    numbers = [int(value) for value in values]
    if len(numbers) not in {2, 3}:
        raise ValueError("GENERATE requires start, end[, increment]")
    start, end = numbers[:2]
    step = numbers[2] if len(numbers) == 3 else 1
    if step == 0:
        raise ValueError("GENERATE increment must not be zero")
    if (end - start) * step < 0:
        raise ValueError("GENERATE increment points away from the end value")
    stop = end + (1 if step > 0 else -1)
    return list(range(start, stop, step))


def _resolve_sets(raw_sets, report, kind):
    resolved = {}
    active = set()

    def resolve(name):
        if name in resolved:
            return resolved[name]
        if name in active:
            report.warnings.append(f"Cyclic {kind} reference involving {name!r} was ignored")
            return []
        active.add(name)
        values = []
        for value in raw_sets.get(name, ()):
            if isinstance(value, int):
                values.append(value)
                continue
            reference = str(value).strip()
            match = next((key for key in raw_sets if key.upper() == reference.upper()), None)
            if match is None:
                report.warnings.append(
                    f"{kind} {name!r} references unknown set {reference!r}"
                )
                continue
            values.extend(resolve(match))
        active.discard(name)
        resolved[name] = sorted(set(int(value) for value in values))
        return resolved[name]

    for name in raw_sets:
        resolve(name)
    return resolved


def _resolve_surfaces(raw_surfaces, element_sets, report):
    surfaces = {}
    for name, rows in raw_surfaces.items():
        facets = []
        for reference, side in rows:
            if isinstance(reference, int):
                element_ids = [reference]
            else:
                match = next(
                    (key for key in element_sets if key.upper() == str(reference).upper()),
                    None,
                )
                if match is None:
                    report.warnings.append(
                        f"SURFACE {name!r} references unknown ELSET {reference!r}"
                    )
                    continue
                element_ids = element_sets[match]
            facets.extend((int(element_id), str(side).upper()) for element_id in element_ids)
        surfaces[name] = sorted(set(facets))
    return surfaces


def _read_pyvista(path, part_id):
    import pyvista as pv
    grid = pv.read(path)
    if not hasattr(grid, "cells_dict"):
        grid = grid.cast_to_unstructured_grid()
    tags = np.asarray(
        grid.point_data.get("node_id", np.arange(1, grid.n_points + 1)),
        np.int64,
    )
    blocks = []
    mapping = {
        3: (1, "Lines", 1, 2, 1),
        5: (2, "Triangles", 1, 3, 2),
        9: (3, "Quadrilaterals", 1, 4, 2),
        10: (4, "Tetrahedra", 1, 4, 3),
        12: (5, "Hexahedra", 1, 8, 3),
        13: (6, "Pentahedra", 1, 6, 3),
        14: (7, "Pyramids", 1, 5, 3),
    }
    next_id = 1
    for vtk_type, connectivity in grid.cells_dict.items():
        if int(vtk_type) not in mapping:
            continue
        gmsh, name, order, primary, dimension = mapping[int(vtk_type)]
        count = len(connectivity)
        blocks.append(
            MeshBlock(
                gmsh,
                name,
                dimension,
                order,
                primary,
                np.asarray(connectivity, np.int64),
                np.arange(next_id, next_id + count, dtype=np.int64),
            )
        )
        next_id += count
    return MeshSnapshot(
        part_id,
        tags,
        np.asarray(grid.points, float),
        blocks,
        max((block.dimension for block in blocks), default=0),
        fingerprint=str(path),
    )
