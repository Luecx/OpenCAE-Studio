"""Schema 23 to 24: split MeshState and type CAD association keys."""

from __future__ import annotations

import re


_GEOMETRY_REF = re.compile(
    r"^\s*(vertex|point|edge|face|surface|cell|volume)\s*[-:#]?\s*(\d+)\s*$",
    re.I,
)
_DIMENSION = {
    "vertex": 0,
    "point": 0,
    "edge": 1,
    "face": 2,
    "surface": 2,
    "cell": 3,
    "volume": 3,
}


def migrate_v23_to_v24(envelope):
    result = dict(envelope)
    result["project"] = _walk(result.get("project"))
    result["schema_version"] = 24
    return result


def _walk(value):
    if isinstance(value, list):
        return [_walk(item) for item in value]
    if not isinstance(value, dict):
        return value
    current = {key: _walk(item) for key, item in value.items()}
    type_name = current.get("__type__")
    if type_name == "node_table":
        ids = current.get("ids", [])
        current.setdefault("origins", ["generated"] * len(ids))
    elif type_name == "element_block":
        ids = current.get("ids", [])
        current.setdefault("origins", ["generated"] * len(ids))
    elif type_name == "mesh_state":
        current = _mesh_state(current)
    elif type_name in {"region", "node_set", "element_set", "surface"}:
        current["definition"] = _region_definition(current.get("definition"))
    return current


def _mesh_state(value):
    origins = _mesh_origins(value)
    status = str(value.get("status", "Not generated"))
    association_nonempty = any(
        bool(value.get(name))
        for name in ("entity_nodes", "entity_elements", "entity_facets")
    )
    if "generated" in origins:
        origin = "generated"
    elif "imported" in origins:
        origin = "imported"
    else:
        origin = "authored"
    authored_status = status.casefold() == "authored"
    lifecycle = {
        "__type__": "mesh_lifecycle_state",
        "origin": origin,
        "edit_state": "Modified" if authored_status else "Clean",
        "validity": (
            "Outdated" if status.casefold() == "outdated" else "Current"
        ),
        "geometry_association": (
            "Detached"
            if authored_status and association_nonempty
            else "Attached" if association_nonempty else "None"
        ),
        "revision": value.get("revision", ""),
    }
    return {
        "__type__": "mesh_state",
        "recipe": {
            "__type__": "meshing_recipe",
            "settings": value.get(
                "settings",
                {"__type__": "mesh_settings"},
            ),
            "seeds": value.get("seeds", []),
            "element_controls": value.get("element_controls", []),
        },
        "finite_elements": {
            "__type__": "finite_element_mesh",
            "nodes": value.get(
                "nodes",
                {
                    "__type__": "node_table",
                    "ids": [],
                    "coordinates": [],
                    "origins": [],
                },
            ),
            "element_definitions": value.get("element_definitions", []),
            "element_blocks": value.get("element_blocks", []),
            "node_count": int(value.get("node_count", 0) or 0),
            "element_count": int(value.get("element_count", 0) or 0),
            "mesh_dimension": int(value.get("mesh_dimension", 0) or 0),
        },
        "associations": {
            "__type__": "mesh_association_store",
            "nodes": _association_map(value.get("entity_nodes", {}), "ids"),
            "elements": _association_map(
                value.get("entity_elements", {}),
                "ids",
            ),
            "facets": _association_map(
                value.get("entity_facets", {}),
                "facets",
            ),
        },
        "quality": {
            "__type__": "mesh_quality_summary",
            "minimum": value.get("minimum_quality"),
            "mean": value.get("mean_quality"),
            "invalid_element_ids": {"__tuple__": []},
            "inverted_element_ids": {"__tuple__": []},
            "degenerate_element_ids": {"__tuple__": []},
        },
        "lifecycle": lifecycle,
    }


def _mesh_origins(value):
    result = set()
    nodes = value.get("nodes") or {}
    result.update(str(item).casefold() for item in nodes.get("origins", ()))
    for block in value.get("element_blocks", ()):
        result.update(
            str(item).casefold()
            for item in block.get("origins", ())
        )
    return result or {"generated"}


def _association_map(values, value_kind):
    entries = []
    for key, members in dict(values or {}).items():
        geometry = _geometry_ref(key)
        if geometry is None:
            continue
        entries.append(
            {
                "__type__": "geometry_association_entry",
                "geometry": geometry,
                "values": members,
            }
        )
    return {
        "__type__": "geometry_association_map",
        "value_kind": value_kind,
        "entries": entries,
    }


def _geometry_ref(value):
    if (
        isinstance(value, dict)
        and value.get("__type__") == "geometry_entity_ref"
    ):
        return value
    match = _GEOMETRY_REF.match(str(value or ""))
    if not match:
        return None
    return {
        "__type__": "geometry_entity_ref",
        "dimension": _DIMENSION[match.group(1).casefold()],
        "tag": int(match.group(2)),
    }


def _region_definition(value):
    if (
        isinstance(value, dict)
        and value.get("__type__") == "region_definition"
    ):
        return value
    if value in (None, "", []):
        labels = []
    elif isinstance(value, str):
        labels = [value]
    elif isinstance(value, (list, tuple)):
        labels = [str(item) for item in value]
    else:
        return value
    return {
        "__type__": "region_definition",
        "items": {
            "__tuple__": [
                {
                    "__type__": "region_selection_item",
                    "operand": {
                        "__type__": "unresolved_operand",
                        "legacy_label": label,
                        "expected_kind": "",
                    },
                    "picked_position": None,
                    "display_label": label,
                }
                for label in labels
            ]
        },
    }
