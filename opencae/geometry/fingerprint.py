from __future__ import annotations

import hashlib
import json
from dataclasses import asdict


def part_fingerprint(part, include_mesh: bool = False) -> str:
    data = {
        "geometry_settings": asdict(part.geometry_settings),
        "geometry": [asdict(feature) for feature in part.geometry],
    }
    if include_mesh:
        data["mesh_settings"] = asdict(part.mesh.settings)
        data["seeds"] = [asdict(seed) for seed in part.mesh.seeds]
    raw = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
