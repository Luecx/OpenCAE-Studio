"""Schema 24 -> 25: reserve registered types for authored sketch geometry."""

from __future__ import annotations

from copy import deepcopy


def migrate_v24_to_v25(data):
    """Bump the envelope; existing model payloads need no structural rewrite."""
    result = deepcopy(data)
    result["schema_version"] = 25
    return result
