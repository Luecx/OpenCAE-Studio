"""Read FEMaster element-nodal beam section forces beside an FRD result.

OpenCAE keeps FRD as the primary visualization result. FEMaster currently writes
``LOCAL_SECTION_FORCES`` only to its native text RES file because FRD supports
NODE-domain fields only. This module reads that auxiliary block lazily when
physical beam rendering needs stress recovery.
"""

from __future__ import annotations

from pathlib import Path
import re

import numpy as np

_FIELD_NAME = "LOCAL_SECTION_FORCES"
_HEADER_VALUE = re.compile(r"([A-Z_]+)=([^,]+)", re.IGNORECASE)


def load_local_section_forces(
    result_source: str | Path,
    step_id: int | None = None,
) -> dict[int, np.ndarray]:
    """Return ordered endpoint resultants ``[N,Vy,Vz,T,My,Mz]`` per element.

    FRD step identifiers are not guaranteed to equal native RES ``LC`` labels.
    Exact LC matches are preferred; otherwise a single LC is unambiguous and a
    multi-LC file falls back to the requested 1-based loadcase ordinal.
    """
    source = Path(result_source)
    path = source if source.suffix.lower() == ".res" else source.with_suffix(".res")
    if not path.is_file():
        return {}

    requested = int(step_id) if step_id is not None else None
    current_loadcase: int | None = None
    collecting = False
    loadcase_order: list[int | None] = []
    grouped: dict[int | None, dict[int, dict[int, np.ndarray]]] = {}

    with path.open("r", errors="replace") as stream:
        for raw_line in stream:
            line = raw_line.strip()
            if line.startswith("LC "):
                try:
                    current_loadcase = int(line.split(maxsplit=1)[1])
                except (IndexError, ValueError):
                    current_loadcase = None
                continue

            if line.startswith("FIELD,"):
                metadata = {
                    key.upper(): value.strip()
                    for key, value in _HEADER_VALUE.findall(line)
                }
                collecting = (
                    metadata.get("NAME", "").upper() == _FIELD_NAME
                    and metadata.get("TYPE", "").upper() == "ELEMENT_NODAL"
                )
                if collecting and current_loadcase not in grouped:
                    grouped[current_loadcase] = {}
                    loadcase_order.append(current_loadcase)
                continue

            if line == "END FIELD":
                collecting = False
                continue

            if not collecting or not line:
                continue

            tokens = line.split()
            if len(tokens) < 8:
                continue
            element_id = _element_id(tokens[0])
            if element_id is None:
                continue
            try:
                local_node = int(tokens[1])
                values = np.asarray([float(value) for value in tokens[2:8]], dtype=float)
            except ValueError:
                continue
            grouped.setdefault(current_loadcase, {}).setdefault(element_id, {})[
                local_node
            ] = values

    selected = _select_loadcase(grouped, loadcase_order, requested)
    if selected is None:
        return {}
    return _pack(grouped[selected])


def _select_loadcase(grouped, order, requested):
    if not order:
        return None
    if requested is not None and requested in grouped:
        return requested
    if len(order) == 1:
        return order[0]
    if requested is not None and 1 <= requested <= len(order):
        return order[requested - 1]
    if requested is None:
        return order[0]
    return None


def _pack(result: dict[int, dict[int, np.ndarray]]) -> dict[int, np.ndarray]:
    packed: dict[int, np.ndarray] = {}
    for element_id, rows in result.items():
        if not rows:
            continue
        # FEMaster currently emits zero-based local locations, while older or
        # foreign RES writers may choose one-based labels. Preserve only their
        # ordering here; recovery consumes row 0 as the first beam end and row 1
        # as the second independent of the textual label convention.
        packed[element_id] = np.vstack(
            [rows[local_node] for local_node in sorted(rows)]
        ).astype(float, copy=False)
    return packed


def _element_id(value: str) -> int | None:
    """Resolve bare or qualified ``instance.element`` RES identifiers."""
    token = str(value).rsplit(".", 1)[-1]
    try:
        return int(token)
    except ValueError:
        return None
