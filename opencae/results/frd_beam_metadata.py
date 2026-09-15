"""Embed and read OpenCAE physical-beam metadata inside one FRD file.

OpenCAE result viewing is intentionally FRD-only. FEMaster may emit a temporary
native RES during a solve; this module extracts only beam section resultants from
that file and stores them, together with profile definitions and transformed n1
vectors, as versioned FRD ``1U`` user records. The resulting FRD is self-contained
and can be opened without the original project or any sidecar file.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable

import numpy as np

from opencae.model.entities.profiles import create_profile
from .beam_physical_model import beam_occurrences
from .frd_parser import parse_frd
from .res_parser import parse_res

_PREFIX = "    1UOCAE "
_SCHEMA = 1
_PROFILE_CHUNK = 32
_SECTION_FORCE_NAMES = {"LOCAL_SECTION_FORCES", "BEAM_SECTION_FORCES"}
_PROFILE_TYPES = {
    "Rectangle": 1,
    "Box": 2,
    "Circle": 3,
    "Pipe": 4,
    "I-profile": 5,
    "H-profile": 6,
    "C-profile": 7,
    "Channel": 7,
    "U-profile": 8,
    "Graph profile": 9,
    "General": 10,
}
_PROFILE_NAMES = {
    1: "Rectangle",
    2: "Box",
    3: "Circle",
    4: "Pipe",
    5: "I-profile",
    6: "H-profile",
    7: "C-profile",
    8: "U-profile",
    9: "Graph profile",
    10: "General",
}


@dataclass(frozen=True, slots=True)
class EmbeddedBeamOccurrence:
    solver_element_id: int
    profile_id: int
    n1: tuple[float, float, float]
    profile: object

    @property
    def direction(self) -> tuple[float, float, float]:
        return self.n1

    @property
    def source_element_id(self) -> int:
        return self.solver_element_id


@dataclass(frozen=True, slots=True)
class FrdBeamMetadata:
    schema: int
    profiles: dict[int, object]
    beams: tuple[EmbeddedBeamOccurrence, ...]
    forces: dict[tuple[int, int], dict[int, np.ndarray]]


def embed_femaster_beam_metadata(project, frd_path: str | Path, res_path: str | Path) -> None:
    """Rewrite one FEMaster FRD with all physical-beam data required by OpenCAE."""
    frd = Path(frd_path)
    if not frd.is_file():
        raise FileNotFoundError(f"FEMaster did not create expected FRD result '{frd.name}'")

    occurrences = beam_occurrences(project)
    if not occurrences:
        _rewrite_metadata(frd, ())
        return

    res = Path(res_path)
    if not res.is_file():
        raise FileNotFoundError(
            "Physical beam post-processing requires FEMaster section forces. "
            f"Expected temporary result '{res.name}'."
        )

    records = list(_model_records(occurrences))
    records.extend(_force_records(frd, res, occurrences))
    _rewrite_metadata(frd, records)


def read_frd_beam_metadata(path: str | Path) -> FrdBeamMetadata:
    """Parse only OpenCAE ``1UOCAE`` records from an FRD file."""
    schema = 0
    profile_parts: dict[int, tuple[int, int, dict[int, str]]] = {}
    beam_rows: list[tuple[int, int, tuple[float, float, float]]] = []
    force_parts: dict[tuple[int, int, int, int], dict[int, tuple[float, ...]]] = {}

    with Path(path).open("r", errors="replace") as stream:
        for raw in stream:
            if not raw.startswith(_PREFIX):
                continue
            tokens = raw[len(_PREFIX):].strip().split()
            if not tokens:
                continue
            tag = tokens[0].upper()
            try:
                if tag == "SCHEMA" and len(tokens) >= 2:
                    schema = int(tokens[1])
                elif tag == "P" and len(tokens) >= 6:
                    profile_id = int(tokens[1])
                    type_id = int(tokens[2])
                    index = int(tokens[3])
                    total = int(tokens[4])
                    current = profile_parts.setdefault(profile_id, (type_id, total, {}))
                    current[2][index] = tokens[5]
                elif tag == "B" and len(tokens) >= 6:
                    beam_rows.append(
                        (
                            int(tokens[1]),
                            int(tokens[2]),
                            (float(tokens[3]), float(tokens[4]), float(tokens[5])),
                        )
                    )
                elif tag in {"F1", "F2"} and len(tokens) >= 9:
                    step = int(tokens[1])
                    frame = int(tokens[2])
                    element = int(tokens[3])
                    end = int(tokens[4])
                    values = tuple(float(value) for value in tokens[5:8])
                    slot = 0 if tag == "F1" else 1
                    force_parts.setdefault((step, frame, element, end), {})[slot] = values
            except (TypeError, ValueError):
                continue

    profiles: dict[int, object] = {}
    for profile_id, (type_id, total, chunks) in profile_parts.items():
        if len(chunks) != total or type_id not in _PROFILE_NAMES:
            continue
        encoded = "".join(chunks[index] for index in range(total))
        try:
            padding = "=" * (-len(encoded) % 4)
            dimensions = json.loads(base64.urlsafe_b64decode(encoded + padding).decode("utf-8"))
            profiles[profile_id] = create_profile(
                _PROFILE_NAMES[type_id],
                name=f"FRD Profile {profile_id}",
                dimensions=dict(dimensions or {}),
            )
        except (ValueError, TypeError, json.JSONDecodeError):
            continue

    beams = tuple(
        EmbeddedBeamOccurrence(element, profile_id, n1, profiles[profile_id])
        for element, profile_id, n1 in beam_rows
        if profile_id in profiles
    )

    forces: dict[tuple[int, int], dict[int, np.ndarray]] = {}
    grouped: dict[tuple[int, int, int], dict[int, np.ndarray]] = {}
    for (step, frame, element, end), parts in force_parts.items():
        if 0 not in parts or 1 not in parts:
            continue
        grouped.setdefault((step, frame, element), {})[end] = np.asarray(
            (*parts[0], *parts[1]), dtype=float
        )
    for (step, frame, element), endpoints in grouped.items():
        if 0 not in endpoints or 1 not in endpoints:
            continue
        forces.setdefault((step, frame), {})[element] = np.vstack(
            (endpoints[0], endpoints[1])
        )

    return FrdBeamMetadata(schema, profiles, beams, forces)


def beam_occurrences_from_frd(path: str | Path) -> tuple[EmbeddedBeamOccurrence, ...]:
    return read_frd_beam_metadata(path).beams


def section_forces_from_frd(
    path: str | Path,
    step_id: int | None = None,
    frame_id: int | None = None,
) -> dict[int, np.ndarray]:
    metadata = read_frd_beam_metadata(path)
    if not metadata.forces:
        return {}
    step = int(step_id or 1)
    frame = int(frame_id or 1)
    exact = metadata.forces.get((step, frame))
    if exact is not None:
        return exact
    same_step = [value for (current_step, _), value in metadata.forces.items() if current_step == step]
    if len(same_step) == 1:
        return same_step[0]
    return {}


def _model_records(occurrences: Iterable) -> Iterable[str]:
    yield f"{_PREFIX}SCHEMA {_SCHEMA}"
    profile_ids: dict[tuple[int, str], int] = {}
    profile_for_occurrence: dict[int, int] = {}
    next_profile_id = 1

    for occurrence in occurrences:
        profile = occurrence.profile
        profile_type = str(getattr(profile, "profile_type", "General"))
        type_id = _PROFILE_TYPES.get(profile_type, _PROFILE_TYPES["General"])
        payload = json.dumps(
            dict(getattr(profile, "dimensions", {}) or {}),
            separators=(",", ":"),
            sort_keys=True,
        )
        encoded = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")
        key = (type_id, encoded)
        profile_id = profile_ids.get(key)
        if profile_id is None:
            profile_id = next_profile_id
            next_profile_id += 1
            profile_ids[key] = profile_id
            chunks = [encoded[index:index + _PROFILE_CHUNK] for index in range(0, len(encoded), _PROFILE_CHUNK)] or [""]
            total = len(chunks)
            for index, chunk in enumerate(chunks):
                yield f"{_PREFIX}P {profile_id} {type_id} {index} {total} {chunk}"
        profile_for_occurrence[int(occurrence.solver_element_id)] = profile_id

    for occurrence in occurrences:
        element = int(occurrence.solver_element_id)
        profile_id = profile_for_occurrence[element]
        n1 = tuple(float(value) for value in occurrence.n1)
        yield (
            f"{_PREFIX}B {element} {profile_id} "
            f"{n1[0]:.9e} {n1[1]:.9e} {n1[2]:.9e}"
        )


def _force_records(frd: Path, res: Path, occurrences: Iterable) -> Iterable[str]:
    valid_elements = {int(item.solver_element_id) for item in occurrences}
    blocks = _res_force_blocks(res)
    if not blocks:
        return ()

    data = parse_frd(frd)
    frames = sorted({(int(block.step_id), int(block.frame_id)) for block in data.fields}) or [(1, 1)]
    step_order = []
    for step, _frame in frames:
        if step not in step_order:
            step_order.append(step)
    loadcases = list(blocks)

    records: list[str] = []
    for step, frame in frames:
        loadcase = step if step in blocks else None
        if loadcase is None and step in step_order:
            index = step_order.index(step)
            if index < len(loadcases):
                loadcase = loadcases[index]
        values_by_element = blocks.get(loadcase, {})
        for element in sorted(valid_elements):
            endpoints = values_by_element.get(element)
            if endpoints is None or endpoints.shape[0] < 2 or endpoints.shape[1] < 6:
                continue
            for end in (0, 1):
                values = endpoints[end, :6]
                records.append(
                    f"{_PREFIX}F1 {step} {frame} {element} {end} "
                    + " ".join(f"{value:.7e}" for value in values[:3])
                )
                records.append(
                    f"{_PREFIX}F2 {step} {frame} {element} {end} "
                    + " ".join(f"{value:.7e}" for value in values[3:6])
                )
    return records


def _res_force_blocks(path: Path) -> dict[int, dict[int, np.ndarray]]:
    data = parse_res(path)
    result: dict[int, dict[int, np.ndarray]] = {}
    for block in data.fields:
        if block.name.upper() not in _SECTION_FORCE_NAMES or block.domain != "ELEMENT_NODAL":
            continue
        grouped: dict[int, dict[int, np.ndarray]] = {}
        for indices, values in block.values.items():
            if len(indices) < 2:
                continue
            try:
                element = int(str(indices[0]).strip())
                local_node = int(str(indices[1]).strip())
            except ValueError:
                continue
            current = np.asarray(values, dtype=float)
            if len(current) < 6:
                continue
            grouped.setdefault(element, {})[local_node] = current[:6]
        packed: dict[int, np.ndarray] = {}
        for element, rows in grouped.items():
            if len(rows) < 2:
                continue
            ordered = [rows[index] for index in sorted(rows)[:2]]
            packed[element] = np.vstack(ordered).astype(float, copy=False)
        if packed:
            result[int(block.loadcase)] = packed
    return result


def _rewrite_metadata(path: Path, records: Iterable[str]) -> None:
    original = path.read_text(errors="replace").splitlines()
    body = [line for line in original if not line.startswith(_PREFIX)]
    header = list(records)
    text = "\n".join((*header, *body)) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)
