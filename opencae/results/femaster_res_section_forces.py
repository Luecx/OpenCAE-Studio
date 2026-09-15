"""Read FEMaster element-nodal beam section forces beside an FRD result.

OpenCAE keeps FRD as the primary visualization result. FEMaster currently writes
``LOCAL_SECTION_FORCES`` only to its native text RES file because FRD supports
NODE-domain fields only. This module reads that one auxiliary block lazily when
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
    """Return ordered endpoint resultants ``[N,Vy,Vz,T,My,Mz]`` per element."""
    source = Path(result_source)
    path = source if source.suffix.lower() == ".res" else source.with_suffix(".res")
    if not path.is_file():
        return {}

    requested = int(step_id) if step_id is not None else None
    current_loadcase: int | None = None
    collecting = False
    active = False
    result: dict[int, dict[int, np.ndarray]] = {}

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
                active = collecting and (
                    requested is None
                    or current_loadcase is None
                    or current_loadcase == requested
                )
                continue

            if line == "END FIELD":
                if active and result and requested is not None:
                    break
                collecting = False
                active = False
                continue

            if not collecting or not active or not line:
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
            result.setdefault(element_id, {})[local_node] = values

    packed: dict[int, np.ndarray] = {}
    for element_id, rows in result.items():
        if not rows:
            continue
        # FEMaster currently emits zero-based local locations, while older or
        # foreign RES writers may choose one-based labels. Preserve only their
        # ordering here; stress recovery consumes row 0 as the first beam end
        # and row 1 as the second independent of the textual label convention.
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
