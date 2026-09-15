"""Embed/read all OpenCAE physical-beam result semantics inside one FRD file."""

from __future__ import annotations

import base64
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable

import numpy as np

from opencae.model.entities.profiles import create_profile
from opencae.model.entities.profiles.section_geometry import section_patches
from .beam_physical_model import beam_occurrences
from .beam_physical_stress import stress_coefficients
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
    def direction(self):
        return self.n1

    @property
    def source_element_id(self):
        return self.solver_element_id


@dataclass(frozen=True, slots=True)
class FrdBeamMetadata:
    schema: int
    profiles: dict[int, object]
    beams: tuple[EmbeddedBeamOccurrence, ...]
    forces: dict[tuple[int, int], dict[int, np.ndarray]]


def embed_femaster_beam_metadata(project, frd_path, res_path) -> None:
    """Make FEMaster's FRD self-contained, using RES only as a temporary source."""
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


def read_frd_beam_metadata(path) -> FrdBeamMetadata:
    """Read the contiguous versioned OpenCAE user-header block from an FRD."""
    schema = 0
    profile_parts: dict[int, tuple[int, int, dict[int, str]]] = {}
    beam_rows = []
    force_parts: dict[tuple[int, int, int, int], dict[int, tuple[float, ...]]] = {}
    seen = False
    with Path(path).open("r", errors="replace") as stream:
        for raw in stream:
            if raw.startswith(_PREFIX):
                seen = True
                tokens = raw[len(_PREFIX):].strip().split()
                if not tokens:
                    continue
                try:
                    tag = tokens[0].upper()
                    if tag == "SCHEMA" and len(tokens) >= 2:
                        schema = int(tokens[1])
                    elif tag == "P" and len(tokens) >= 6:
                        profile_id, type_id = int(tokens[1]), int(tokens[2])
                        index, total = int(tokens[3]), int(tokens[4])
                        current = profile_parts.setdefault(profile_id, (type_id, total, {}))
                        current[2][index] = tokens[5]
                    elif tag == "B" and len(tokens) >= 6:
                        beam_rows.append((
                            int(tokens[1]),
                            int(tokens[2]),
                            (float(tokens[3]), float(tokens[4]), float(tokens[5])),
                        ))
                    elif tag in {"F1", "F2"} and len(tokens) >= 8:
                        key = (
                            int(tokens[1]), int(tokens[2]),
                            int(tokens[3]), int(tokens[4]),
                        )
                        force_parts.setdefault(key, {})[0 if tag == "F1" else 1] = tuple(
                            float(value) for value in tokens[5:8]
                        )
                except (TypeError, ValueError):
                    continue
                continue
            if seen or raw.startswith(("    2C", "    3C", "  100C")):
                break

    profiles = {}
    for profile_id, (type_id, total, chunks) in profile_parts.items():
        if type_id not in _PROFILE_NAMES or len(chunks) != total:
            continue
        try:
            encoded = "".join(chunks[index] for index in range(total))
            padding = "=" * (-len(encoded) % 4)
            dimensions = json.loads(
                base64.urlsafe_b64decode(encoded + padding).decode("utf-8")
            )
            profiles[profile_id] = create_profile(
                _PROFILE_NAMES[type_id],
                name=f"FRD Profile {profile_id}",
                dimensions=dict(dimensions or {}),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue

    beams = tuple(
        EmbeddedBeamOccurrence(element, profile_id, n1, profiles[profile_id])
        for element, profile_id, n1 in beam_rows
        if profile_id in profiles
    )

    grouped: dict[tuple[int, int, int], dict[int, np.ndarray]] = {}
    for (step, frame, element, end), parts in force_parts.items():
        if 0 not in parts or 1 not in parts:
            continue
        grouped.setdefault((step, frame, element), {})[end] = np.asarray(
            (*parts[0], *parts[1]), dtype=float
        )
    forces: dict[tuple[int, int], dict[int, np.ndarray]] = {}
    for (step, frame, element), endpoints in grouped.items():
        if 0 in endpoints and 1 in endpoints:
            forces.setdefault((step, frame), {})[element] = np.vstack(
                (endpoints[0], endpoints[1])
            )
    return FrdBeamMetadata(schema, profiles, beams, forces)


def beam_occurrences_from_frd(path):
    return read_frd_beam_metadata(path).beams


def section_forces_from_frd(path, step_id=None, frame_id=None):
    metadata = read_frd_beam_metadata(path)
    if not metadata.forces:
        return {}
    step, frame = int(step_id or 1), int(frame_id or 1)
    exact = metadata.forces.get((step, frame))
    if exact is not None:
        return exact
    same_step = [
        values for (current_step, _), values in metadata.forces.items()
        if current_step == step
    ]
    return same_step[0] if len(same_step) == 1 else {}


def beam_normal_stress_range(path, step_id=None, frame_id=None):
    """Return axial+bending extrema over all embedded profile-patch vertices."""
    metadata = read_frd_beam_metadata(path)
    forces = metadata.forces.get((int(step_id or 1), int(frame_id or 1)), {})
    extrema = []
    for occurrence in metadata.beams:
        endpoints = forces.get(int(occurrence.solver_element_id))
        if endpoints is None:
            continue
        properties = occurrence.profile.properties()
        for patch in section_patches(occurrence.profile):
            for y, z in np.asarray(patch, dtype=float):
                axial, my, mz = stress_coefficients(properties, float(y), float(z))
                for row in endpoints[:2]:
                    extrema.append(float(axial * row[0] + my * row[4] + mz * row[5]))
    finite = np.asarray(extrema, dtype=float)
    finite = finite[np.isfinite(finite)]
    return (float(finite.min()), float(finite.max())) if len(finite) else None


def _model_records(occurrences: Iterable):
    yield f"{_PREFIX}SCHEMA {_SCHEMA}"
    profile_ids = {}
    element_profiles = {}
    for occurrence in occurrences:
        profile = occurrence.profile
        profile_type = str(getattr(profile, "profile_type", "General"))
        type_id = _PROFILE_TYPES.get(profile_type, _PROFILE_TYPES["General"])
        payload = json.dumps(
            dict(getattr(profile, "dimensions", {}) or {}),
            separators=(",", ":"), sort_keys=True,
        )
        encoded = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
        key = (type_id, encoded)
        profile_id = profile_ids.get(key)
        if profile_id is None:
            profile_id = len(profile_ids) + 1
            profile_ids[key] = profile_id
            chunks = [
                encoded[index:index + _PROFILE_CHUNK]
                for index in range(0, len(encoded), _PROFILE_CHUNK)
            ] or [""]
            for index, chunk in enumerate(chunks):
                yield f"{_PREFIX}P {profile_id} {type_id} {index} {len(chunks)} {chunk}"
        element_profiles[int(occurrence.solver_element_id)] = profile_id
    for occurrence in occurrences:
        element = int(occurrence.solver_element_id)
        n1 = tuple(float(value) for value in occurrence.n1)
        yield (
            f"{_PREFIX}B {element} {element_profiles[element]} "
            f"{n1[0]:.9e} {n1[1]:.9e} {n1[2]:.9e}"
        )


def _force_records(frd: Path, res: Path, occurrences: Iterable):
    valid_elements = {int(item.solver_element_id) for item in occurrences}
    raw_blocks = _res_force_blocks(res)
    blocks = {
        loadcase: _normalize_force_ids(values, valid_elements)
        for loadcase, values in raw_blocks.items()
    }
    if not blocks:
        return ()

    data = parse_frd(frd)
    frames = sorted({
        (int(block.step_id), int(block.frame_id)) for block in data.fields
    }) or [(1, 1)]
    step_order = []
    for step, _ in frames:
        if step not in step_order:
            step_order.append(step)
    loadcases = list(blocks)

    records = []
    for step, frame in frames:
        loadcase = step if step in blocks else None
        if loadcase is None:
            index = step_order.index(step)
            loadcase = loadcases[index] if index < len(loadcases) else None
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
                    + " ".join(f"{value:.7e}" for value in values[3:])
                )
    return records


def _normalize_force_ids(values: dict[int, np.ndarray], valid: set[int]):
    """Accept FEMaster's element indices whether its RES writer is 0- or 1-based."""
    if not values or not valid:
        return {}
    exact = len(set(values) & valid)
    plus_one = len({value + 1 for value in values} & valid)
    minus_one = len({value - 1 for value in values} & valid)
    offset = 0
    if plus_one > exact and plus_one >= minus_one:
        offset = 1
    elif minus_one > exact:
        offset = -1
    return {
        int(element) + offset: rows
        for element, rows in values.items()
        if int(element) + offset in valid
    }


def _res_force_blocks(path: Path):
    result = {}
    for block in parse_res(path).fields:
        if block.name.upper() not in _SECTION_FORCE_NAMES or block.domain != "ELEMENT_NODAL":
            continue
        grouped = {}
        for indices, values in block.values.items():
            if len(indices) < 2:
                continue
            try:
                element, local_node = int(indices[0]), int(indices[1])
            except (TypeError, ValueError):
                continue
            current = np.asarray(values, dtype=float)
            if len(current) >= 6:
                grouped.setdefault(element, {})[local_node] = current[:6]
        packed = {}
        for element, rows in grouped.items():
            if len(rows) >= 2:
                packed[element] = np.vstack(
                    [rows[index] for index in sorted(rows)[:2]]
                ).astype(float, copy=False)
        if packed:
            result[int(block.loadcase)] = packed
    return result


def _rewrite_metadata(path: Path, records: Iterable[str]) -> None:
    body = [
        line for line in path.read_text(errors="replace").splitlines()
        if not line.startswith(_PREFIX)
    ]
    text = "\n".join((*list(records), *body)) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)
