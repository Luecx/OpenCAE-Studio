from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, TextIO

import numpy as np


@dataclass(frozen=True, slots=True)
class ResField:
    name: str
    domain: str
    values: np.ndarray
    indices: np.ndarray | None = None


class ResFormatError(ValueError):
    pass


class ResFieldReader:
    """Streaming reader for FEMaster's native text ``.res`` format."""

    def read_fields(
        self,
        path: str | Path,
        *,
        names: Iterable[str] | None = None,
        loadcase_id: int | None = None,
    ) -> dict[str, ResField]:
        wanted = {str(value).upper() for value in names} if names is not None else None
        result: dict[str, ResField] = {}
        active_loadcase: int | None = None
        source = Path(path)
        with source.open("r", encoding="utf-8", errors="replace") as stream:
            iterator = enumerate(stream, start=1)
            for line_number, raw in iterator:
                line = raw.strip()
                if not line or _comment(line):
                    continue
                upper = line.upper()
                if upper.startswith(("LC ", "LOADCASE ")):
                    active_loadcase = _loadcase_id(line, line_number)
                    continue
                if not upper.startswith("FIELD"):
                    continue
                header = _field_header(line, line_number)
                selected_loadcase = loadcase_id is None or active_loadcase == int(loadcase_id)
                selected_name = wanted is None or header["NAME"].upper() in wanted
                field = self._read_field(iterator, header, line_number, selected_loadcase and selected_name)
                if field is not None:
                    result[field.name.upper()] = field
        missing = set() if wanted is None else wanted - set(result)
        if missing:
            raise ResFormatError(
                f"Missing FEMaster result field(s): {', '.join(sorted(missing))}"
            )
        return result

    def _read_field(self, iterator, header, header_line: int, keep: bool) -> ResField | None:
        rows = int(header["ROWS"])
        dense_cols = int(header.get("COLS", 0))
        index_cols = int(header.get("INDEX_COLS", 0))
        value_cols = int(header.get("VALUE_COLS", dense_cols))
        total_cols = dense_cols if dense_cols else index_cols + value_cols
        values = np.empty((rows, value_cols), dtype=float) if keep else None
        indices = np.empty((rows, index_cols), dtype=np.int64) if keep and index_cols else None
        count = 0
        ended = False

        for line_number, raw in iterator:
            line = raw.strip()
            if not line or _comment(line):
                continue
            if line.upper().startswith("END FIELD"):
                ended = True
                break
            if count >= rows:
                raise ResFormatError(
                    f"Field {header['NAME']!r} has more than ROWS={rows} values "
                    f"(line {line_number})"
                )
            tokens = line.replace(",", " ").split()
            if len(tokens) != total_cols:
                raise ResFormatError(
                    f"Field {header['NAME']!r} expects {total_cols} columns, "
                    f"got {len(tokens)} at line {line_number}"
                )
            if keep:
                try:
                    numeric = np.asarray([float(token) for token in tokens], dtype=float)
                except ValueError as exc:
                    raise ResFormatError(
                        f"Invalid numeric value in field {header['NAME']!r} "
                        f"at line {line_number}"
                    ) from exc
                if index_cols:
                    indices[count] = numeric[:index_cols].astype(np.int64)
                values[count] = numeric[index_cols:]
            count += 1

        if not ended:
            raise ResFormatError(
                f"Field {header['NAME']!r} starting at line {header_line} "
                "is missing END FIELD"
            )
        if count != rows:
            raise ResFormatError(
                f"Field {header['NAME']!r} declares ROWS={rows} but contains {count} rows"
            )
        if not keep:
            return None
        return ResField(header["NAME"], header.get("TYPE", "UNKNOWN"), values, indices)


def dense_values(field: ResField, solver_ids: np.ndarray) -> np.ndarray:
    """Select dense FEMaster rows by solver element/node id.

    FEMaster fields are indexed by the internal id, so a mesh exported with ids
    1..N normally has an unused row 0. This helper makes that mapping explicit.
    """

    if field.indices is not None:
        lookup = {int(row[0]): index for index, row in enumerate(field.indices)}
        try:
            rows = [lookup[int(value)] for value in solver_ids]
        except KeyError as exc:
            raise ResFormatError(
                f"Result field {field.name!r} has no row for solver id {exc.args[0]}"
            ) from exc
        return np.asarray(field.values[rows], dtype=float)
    ids = np.asarray(solver_ids, dtype=np.int64)
    if ids.size and (ids.min() < 0 or ids.max() >= len(field.values)):
        raise ResFormatError(
            f"Result field {field.name!r} has {len(field.values)} rows but "
            f"solver id range is {ids.min()}..{ids.max()}"
        )
    return np.asarray(field.values[ids], dtype=float)


def _field_header(line: str, line_number: int) -> dict[str, str]:
    tokens = [token.strip() for token in line.split(",")]
    if not tokens or tokens[0].upper() != "FIELD":
        raise ResFormatError(f"Invalid FIELD header at line {line_number}")
    result = {}
    for token in tokens[1:]:
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        result[key.strip().upper()] = value.strip()
    for key in ("NAME", "ROWS"):
        if key not in result:
            raise ResFormatError(f"FIELD header at line {line_number} lacks {key}")
    if "COLS" not in result and "VALUE_COLS" not in result:
        raise ResFormatError(
            f"FIELD header for {result['NAME']!r} at line {line_number} lacks COLS"
        )
    return result


def _loadcase_id(line: str, line_number: int) -> int:
    pieces = line.replace(",", " ").split()
    if len(pieces) < 2:
        raise ResFormatError(f"Invalid loadcase header at line {line_number}")
    try:
        return int(pieces[1])
    except ValueError as exc:
        raise ResFormatError(f"Invalid loadcase id at line {line_number}") from exc


def _comment(line: str) -> bool:
    return line.startswith(("#", "!", "//", "**"))
