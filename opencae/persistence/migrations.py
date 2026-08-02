from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable

import opencae.model.entities  # register model types
from opencae.core.ids import new_id
from opencae.model.core.entity import Entity
from opencae.model.core.model_registry import MODEL_TYPES

CURRENT_SCHEMA_VERSION = 13
POLYMORPHIC_NAME_REFERENCE_VERSION = 11


@dataclass(slots=True)
class MigrationReport:
    source_version: int
    target_version: int = CURRENT_SCHEMA_VERSION
    changes: list[str] = field(default_factory=list)

    @property
    def migrated(self) -> bool:
        return self.source_version != self.target_version or bool(self.changes)


Migration = Callable[[dict[str, Any], MigrationReport], dict[str, Any]]


def migrate_project_data(data: dict[str, Any]) -> tuple[dict[str, Any], MigrationReport]:
    """Return a migrated copy of an OpenCAE project dictionary.

    Files without ``schema_version`` but with a polymorphic ``__type__`` marker
    are the last name-reference format and are treated as schema 11.  The older
    non-polymorphic format continues to be handled by the legacy loader.
    """
    if not isinstance(data, dict):
        raise TypeError("OpenCAE project data must be a JSON object")
    result = deepcopy(data)
    source_version = _schema_version(result)
    report = MigrationReport(source_version)
    if not result.get("__type__"):
        return result, report
    if source_version > CURRENT_SCHEMA_VERSION:
        raise ValueError(
            f"Project schema {source_version} is newer than supported schema "
            f"{CURRENT_SCHEMA_VERSION}"
        )
    version = source_version
    while version < CURRENT_SCHEMA_VERSION:
        migration = _MIGRATIONS.get(version)
        if migration is None:
            raise ValueError(f"No project migration is available from schema {version}")
        result = migration(result, report)
        version += 1
        result["schema_version"] = version
    result["schema_version"] = CURRENT_SCHEMA_VERSION
    return result, report


def _schema_version(data: dict[str, Any]) -> int:
    raw = data.get("schema_version")
    if raw is None:
        return POLYMORPHIC_NAME_REFERENCE_VERSION if data.get("__type__") else 0
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid project schema version: {raw!r}") from exc


def _migrate_11_to_12(data: dict[str, Any], report: MigrationReport) -> dict[str, Any]:
    _ensure_entity_ids(data, report)
    _walk_and_convert(data, report)
    report.changes.append("Converted mutable name references to typed entity references")
    return data




def _migrate_12_to_13(data: dict[str, Any], report: MigrationReport) -> dict[str, Any]:
    """Mark region-member ownership for contextual binding after decoding.

    Schema 12 already carries stable Entity IDs, but region members can still
    be legacy labels such as ``P-1.Face-3``. Their owner can only be resolved
    reliably with the complete decoded project graph, so the binding pass
    converts them to ``RegionMemberRef`` immediately after this migration.
    """
    report.changes.append("Converted region members to stable owner and entity references")
    return data

def _ensure_entity_ids(value: Any, report: MigrationReport) -> None:
    if isinstance(value, list):
        for item in value:
            _ensure_entity_ids(item, report)
        return
    if not isinstance(value, dict):
        return
    type_name = value.get("__type__")
    cls = MODEL_TYPES.get(type_name)
    if cls is not None and isinstance(cls, type) and issubclass(cls, Entity) and not value.get("id"):
        value["id"] = new_id("entity")
        report.changes.append(f"Added missing ID to {type_name} {value.get('name', '')!r}")
    for item in value.values():
        _ensure_entity_ids(item, report)


def _walk_and_convert(value: Any, report: MigrationReport) -> None:
    if isinstance(value, list):
        for item in value:
            _walk_and_convert(item, report)
        return
    if not isinstance(value, dict):
        return
    for item in list(value.values()):
        _walk_and_convert(item, report)
    _convert_object(value)


def _convert_object(value: dict[str, Any]) -> None:
    type_name = value.get("__type__", "")

    if type_name == "instance":
        _move_ref(value, "part_name", "part_ref", "Part")

    if type_name in {
        "section", "solid_section", "shell_section", "membrane_section",
        "beam_section", "truss_section", "cohesive_section",
    }:
        _move_optional_ref(value, "material_name", "material_ref", "Material")
        _move_optional_ref(value, "profile_name", "profile_ref", "Profile")

    if type_name == "section_assignment":
        _move_ref(value, "section_name", "section_ref", "Section")
        _move_ref(value, "region_name", "region_ref", "ElementSet")
        _move_optional_ref(value, "orientation_name", "orientation_ref", "Orientation", ignored={"Global"})

    if type_name == "orientation":
        _move_ref(value, "region_name", "region_ref", "ElementSet")
        _move_optional_ref(
            value, "coordinate_system_name", "coordinate_system_ref", "CoordinateSystem", ignored={"Global"}
        )

    if type_name == "field_definition":
        _move_optional_ref(value, "region_name", "region_ref", "Region")

    if type_name in _LOAD_TYPES | _SUPPORT_TYPES:
        if "target" not in value and "region_name" in value:
            name = value.pop("region_name", "")
            value["target"] = _entity_target(name, _target_kind(type_name)) if name else None
        else:
            value.pop("region_name", None)
        _move_optional_ref(value, "coordinate_system", "coordinate_system_ref", "CoordinateSystem", ignored={"Global"})
        value.pop("step_name", None)

    if type_name == "temperature_load":
        _move_optional_ref(value, "temperature_field", "temperature_field_ref", "FieldDefinition")

    if type_name == "analysis_step":
        _move_ref_list(value, "active_loads", "load_refs", "Load")
        _move_ref_list(value, "active_supports", "support_refs", "Support")

    if type_name == "job":
        _move_optional_ref(value, "analysis_name", "analysis_ref", "Analysis", ignored={"All Steps"})

    if type_name == "result_set":
        _move_optional_ref(value, "job_name", "job_ref", "Job", ignored={"External"})

    if type_name in _CONSTRAINT_TYPES:
        parameters = value.get("parameters") if isinstance(value.get("parameters"), dict) else {}
        slave_kind = parameters.get("slave_type") or _constraint_slave_kind(type_name)
        value["master"] = _constraint_reference(value.get("master"), "Reference Point")
        value["slave"] = _constraint_reference(value.get("slave"), str(slave_kind))
        if "components" not in value and "components" in parameters:
            value["components"] = parameters.pop("components")
        if "adjust" not in value and "adjust" in parameters:
            value["adjust"] = parameters.pop("adjust")
        if "distance" not in value and "distance" in parameters:
            value["distance"] = parameters.pop("distance")
        parameters.pop("slave_type", None)
        value["parameters"] = parameters


def _move_ref(value: dict[str, Any], old: str, new: str, expected: str) -> None:
    if new not in value:
        value[new] = _entity_ref(value.get(old, ""), expected)
    value.pop(old, None)


def _move_optional_ref(
    value: dict[str, Any], old: str, new: str, expected: str, ignored: set[str] | None = None
) -> None:
    ignored = ignored or set()
    if new not in value:
        name = value.get(old, "")
        value[new] = None if name in ignored or name in (None, "") else _entity_ref(name, expected)
    value.pop(old, None)


def _move_ref_list(value: dict[str, Any], old: str, new: str, expected: str) -> None:
    if new not in value:
        value[new] = [_entity_ref(item, expected) for item in value.get(old, ())]
    value.pop(old, None)


def _entity_ref(value: Any, expected: str) -> dict[str, Any]:
    if isinstance(value, dict) and value.get("__type__") == "entity_ref":
        result = dict(value)
        if expected and not result.get("expected_type"):
            result["expected_type"] = expected
        return result
    if isinstance(value, dict) and value.get("id"):
        return {"__type__": "entity_ref", "entity_id": str(value["id"]), "expected_type": expected, "legacy_name": ""}
    return {
        "__type__": "entity_ref",
        "entity_id": "",
        "expected_type": expected,
        "legacy_name": str(value or ""),
    }


def _entity_target(value: Any, kind: str) -> dict[str, Any]:
    known = {
        "entity_target", "node_set_target", "element_set_target", "surface_target",
        "reference_point_target", "whole_model_target", "mesh_node_target", "mesh_element_target",
    }
    if isinstance(value, dict) and value.get("__type__") in known:
        return value
    target_type = {
        "Node Set": "node_set_target", "Element Set": "element_set_target",
        "Surface": "surface_target", "Reference Point": "reference_point_target",
        "Whole Model": "whole_model_target",
    }.get(kind, "entity_target")
    result = {"__type__": target_type, "ref": _entity_ref(value, kind.replace(" ", ""))}
    if target_type == "entity_target":
        result["kind"] = kind
    return result


def _constraint_reference(value: Any, kind: str) -> dict[str, Any]:
    if isinstance(value, dict) and value.get("__type__") == "constraint_reference":
        result = dict(value)
        result.pop("name", None)
        result["kind"] = result.get("kind") or kind
        if "ref" not in result:
            result["ref"] = _entity_ref("", kind.replace(" ", ""))
        return result
    if isinstance(value, dict):
        name = value.get("name", "")
        ref = value.get("ref") or _entity_ref(name, kind.replace(" ", ""))
        return {"__type__": "constraint_reference", "kind": value.get("kind") or kind, "ref": ref}
    return {"__type__": "constraint_reference", "kind": kind, "ref": _entity_ref(value, kind.replace(" ", ""))}


def _target_kind(type_name: str) -> str:
    if type_name in {"pressure_load", "distributed_load"}:
        return "Surface"
    if type_name in {"volume_load", "inertia_load", "gravity_load", "body_load"}:
        return "Element Set"
    return "Node Set"


def _constraint_slave_kind(type_name: str) -> str:
    if type_name == "tie_constraint":
        return "Surface"
    return "Node Set"


_LOAD_TYPES = {
    "load", "concentrated_load", "force_load", "moment_load", "distributed_load",
    "pressure_load", "volume_load", "gravity_load", "body_load", "inertia_load", "temperature_load",
}
_SUPPORT_TYPES = {
    "support", "fixed_support", "displacement_support", "remote_displacement_support",
    "symmetry_support", "temperature_support",
}
_CONSTRAINT_TYPES = {
    "constraint", "kinematic_coupling", "distributing_coupling", "tie_constraint",
    "rigid_body_constraint", "equation_constraint", "mpc_constraint",
}

_MIGRATIONS: dict[int, Migration] = {
    POLYMORPHIC_NAME_REFERENCE_VERSION: _migrate_11_to_12,
    12: _migrate_12_to_13,
}
