"""Migrates schema-20 meshes to one canonical element-definition owner.

Schema 20 serialized each ``ElementDefinition`` both in ``MeshState.elements``
and again inside every ``ElementBlock``. Schema 21 owns definitions once in
``MeshState.element_definitions`` and stores only stable references in blocks.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from opencae.core.ids import new_id

SOURCE_SCHEMA_VERSION = 20
TARGET_SCHEMA_VERSION = 21


def migrate_mesh_definitions(data: dict[str, Any]) -> dict[str, Any]:
    """Return a schema-21 copy with duplicated mesh definitions normalized."""
    if not isinstance(data, dict):
        raise TypeError("OpenCAE project data must be a JSON object")
    try:
        version = int(data.get("schema_version"))
    except (TypeError, ValueError) as exc:
        raise ValueError("The project file has no valid schema version") from exc
    if version != SOURCE_SCHEMA_VERSION:
        raise ValueError(
            f"Mesh-definition migration requires schema "
            f"{SOURCE_SCHEMA_VERSION}, got {version}"
        )

    result = deepcopy(data)
    _walk(result)
    result["schema_version"] = TARGET_SCHEMA_VERSION
    return result


def _walk(value: Any) -> None:
    """Find every persisted MeshState and normalize its definition ownership."""
    if isinstance(value, list):
        for item in value:
            _walk(item)
        return
    if not isinstance(value, dict):
        return

    if value.get("__type__") == "mesh_state":
        _migrate_mesh(value)
    for item in value.values():
        _walk(item)


def _migrate_mesh(mesh: dict[str, Any]) -> None:
    """Move definitions to one list and replace block copies with references."""
    definitions: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    by_key: dict[tuple[Any, ...], dict[str, Any]] = {}

    for definition in (
        *(mesh.pop("elements", ()) or ()),
        *(mesh.pop("element_definitions", ()) or ()),
    ):
        if isinstance(definition, dict):
            _remember_definition(definition, definitions, by_id, by_key)

    counts: dict[str, int] = {}
    for block in mesh.get("element_blocks", ()) or ():
        if not isinstance(block, dict):
            continue
        definition = _definition_for_block(block, by_id, by_key)
        if definition is None:
            embedded = block.get("definition")
            if not isinstance(embedded, dict):
                raise ValueError(
                    "Schema-20 ElementBlock has no resolvable definition"
                )
            definition = _remember_definition(
                embedded,
                definitions,
                by_id,
                by_key,
            )

        definition_id = _ensure_definition_id(definition)
        block.pop("definition", None)
        block["definition_ref"] = _entity_ref(definition_id)
        counts[definition_id] = counts.get(definition_id, 0) + len(
            block.get("ids") or ()
        )

    for definition in definitions:
        definition_id = _ensure_definition_id(definition)
        if definition_id in counts:
            definition["count"] = counts[definition_id]
    mesh["element_definitions"] = definitions


def _definition_for_block(
    block: dict[str, Any],
    by_id: dict[str, dict[str, Any]],
    by_key: dict[tuple[Any, ...], dict[str, Any]],
) -> dict[str, Any] | None:
    """Resolve a schema-20 block copy to an already canonical definition."""
    reference = block.get("definition_ref")
    if isinstance(reference, dict):
        definition = by_id.get(str(reference.get("entity_id") or ""))
        if definition is not None:
            return definition

    embedded = block.get("definition")
    if not isinstance(embedded, dict):
        return None
    definition = by_id.get(str(embedded.get("id") or ""))
    if definition is not None:
        return definition
    return by_key.get(_definition_key(embedded))


def _remember_definition(
    definition: dict[str, Any],
    definitions: list[dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
    by_key: dict[tuple[Any, ...], dict[str, Any]],
) -> dict[str, Any]:
    """Register or reuse one canonical persisted ElementDefinition dictionary."""
    definition_id = str(definition.get("id") or "")
    if definition_id and definition_id in by_id:
        return by_id[definition_id]

    key = _definition_key(definition)
    existing = by_key.get(key)
    if existing is not None:
        if definition_id:
            by_id[definition_id] = existing
        return existing

    definition_id = _ensure_definition_id(definition)
    definitions.append(definition)
    by_id[definition_id] = definition
    by_key[key] = definition
    return definition


def _ensure_definition_id(definition: dict[str, Any]) -> str:
    """Ensure a migrated Entity dictionary has the stable ID needed by refs."""
    definition_id = str(definition.get("id") or "")
    if not definition_id:
        definition_id = new_id("entity")
        definition["id"] = definition_id
    return definition_id


def _definition_key(definition: dict[str, Any]) -> tuple[Any, ...]:
    """Return identity-independent metadata for schema-20 alias matching."""
    return (
        str(definition.get("__type__") or "element_definition"),
        str(definition.get("name") or ""),
        str(definition.get("category") or ""),
        str(definition.get("topology") or ""),
        str(definition.get("order") or ""),
        str(definition.get("formulation") or ""),
        int(definition.get("gmsh_type") or 0),
    )


def _entity_ref(entity_id: str) -> dict[str, Any]:
    """Build the persisted typed reference used by schema-21 ElementBlocks."""
    return {
        "__type__": "entity_ref",
        "entity_id": entity_id,
        "expected_type": "ElementDefinition",
        "legacy_name": "",
    }
