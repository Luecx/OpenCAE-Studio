"""Builds stable cache fingerprints from persisted geometry and mesh state.

Runtime ownership links such as ``Entity._project`` are deliberately excluded.
The fingerprint follows the same serialization boundary as persisted model data
instead of recursively walking the live object graph.
"""

from __future__ import annotations

import hashlib
import json

from opencae.model.core import encode_model


def part_fingerprint(part, include_mesh: bool = False) -> str:
    """Return a deterministic hash of the part state relevant to geometry builds.

    ``dataclasses.asdict`` must not be used here: model entities are bound back
    to their owning Project at runtime, which makes the live dataclass graph
    cyclic. ``encode_model`` respects ``serialize=False`` fields and therefore
    produces the same acyclic representation used by persistence.
    """
    data = {
        "geometry_settings": encode_model(part.geometry_settings),
        "geometry": [encode_model(feature) for feature in part.geometry],
    }
    if include_mesh:
        data["mesh_settings"] = encode_model(part.mesh.settings)
        data["seeds"] = [encode_model(seed) for seed in part.mesh.seeds]

    raw = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
