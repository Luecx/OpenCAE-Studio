"""Read FEMaster LOCAL_SECTION_FORCES from a directly selected native RES."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .res_parser import parse_res

_FIELD_NAME = "LOCAL_SECTION_FORCES"


def load_local_section_forces(
    result_source: str | Path,
    step_id: int | None = None,
) -> dict[int, np.ndarray]:
    """Return ordered endpoint rows ``[N,Vy,Vz,T,My,Mz]`` by solver element id."""
    path = Path(result_source)
    if path.suffix.lower() != ".res" or not path.is_file():
        return {}

    data = parse_res(path)
    candidates = [
        block
        for block in data.fields
        if block.name.upper() == _FIELD_NAME
        and block.domain == "ELEMENT_NODAL"
    ]
    if not candidates:
        return {}

    order = list(dict.fromkeys(block.loadcase for block in candidates))
    selected = _select_loadcase(order, step_id)
    block = next(
        (item for item in candidates if item.loadcase == selected),
        None,
    )
    if block is None:
        return {}

    try:
        from .res_loader import ResLoader

        element_map = ResLoader().element_id_map(path)
    except (OSError, RuntimeError, TypeError, ValueError):
        element_map = {}

    grouped: dict[int, dict[int, np.ndarray]] = {}
    for indices, current in block.values.items():
        if len(indices) < 2:
            continue
        element_id = _element_id(indices[0], element_map)
        if element_id is None:
            continue
        try:
            local_node = int(indices[1])
        except (TypeError, ValueError):
            continue
        values = np.asarray(current, dtype=float)
        if len(values) < 6:
            continue
        grouped.setdefault(element_id, {})[local_node] = values[:6]
    return _pack(grouped)


def _element_id(token, element_map) -> int | None:
    text = str(token).strip()
    if text in element_map:
        return int(element_map[text])
    try:
        return int(text)
    except ValueError:
        return None


def _select_loadcase(order, requested):
    if not order:
        return None
    if requested is not None:
        requested = int(requested)
        if requested in order:
            return requested
    if len(order) == 1:
        return order[0]
    if requested is not None and 1 <= requested <= len(order):
        return order[requested - 1]
    return order[0] if requested is None else None


def _pack(grouped):
    result = {}
    for element_id, rows in grouped.items():
        if rows:
            result[int(element_id)] = np.vstack(
                [rows[index] for index in sorted(rows)]
            ).astype(float, copy=False)
    return result
