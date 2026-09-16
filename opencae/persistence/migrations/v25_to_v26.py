"""Schema 25 -> 26: rename the persisted beam-section direction to n1."""

from __future__ import annotations

from copy import deepcopy


_DEFAULT_N1 = {"__tuple__": [0.0, 1.0, 0.0]}


def migrate_v25_to_v26(data):
    """Rename legacy BeamSection ``direction`` fields without losing values."""
    result = deepcopy(data)
    result["project"] = _walk(result.get("project"))
    result["schema_version"] = 26
    return result


def _walk(value):
    if isinstance(value, list):
        return [_walk(item) for item in value]
    if not isinstance(value, dict):
        return value

    current = {key: _walk(item) for key, item in value.items()}
    if current.get("__type__") == "beam_section":
        legacy = current.pop("direction", None)
        current.setdefault("n1", legacy if legacy is not None else deepcopy(_DEFAULT_N1))
    return current
