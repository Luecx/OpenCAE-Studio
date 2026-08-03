from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable

import opencae.model.entities  # register model types
from opencae.core.ids import new_id
from opencae.model.core.entity import Entity
from opencae.model.core.model_registry import MODEL_TYPES

CURRENT_SCHEMA_VERSION = 19
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
    """Mark legacy region members for contextual conversion in schema 14."""
    report.changes.append("Converted region members to stable owner and entity references")
    return data


def _migrate_13_to_14(data: dict[str, Any], report: MigrationReport) -> dict[str, Any]:
    """Replace target/reference special cases with generic RegionDefinition values."""
    _walk_13_to_14(data)
    report.changes.extend([
        "Unified Part and Assembly node sets, element sets and surfaces into one regions collection",
        "Converted region members and direct targets to generic RegionDefinition operands",
        "Converted section assignments and constraints to region-based targets",
        "Added explicit mesh revision tracking for persistent mesh selections",
    ])
    return data


def _walk_13_to_14(value: Any) -> None:
    if isinstance(value, list):
        for item in value: _walk_13_to_14(item)
        return
    if not isinstance(value, dict): return
    for item in list(value.values()): _walk_13_to_14(item)
    type_name = value.get("__type__", "")
    if type_name in {"part", "assembly"}:
        regions = list(value.get("regions") or ())
        for key, projection in (("node_sets", "nodes"), ("element_sets", "elements"), ("surfaces", "facets")):
            for region in value.pop(key, ()) or ():
                if isinstance(region, dict): region.setdefault("preferred_projection", projection)
                regions.append(region)
        value["regions"] = regions
    if type_name in {"region", "node_set", "element_set", "surface"}:
        if "definition" not in value:
            value["definition"] = _definition_from_members(value.pop("members", ()))
        value.pop("region_type", None)
        if type_name == "node_set": value["preferred_projection"] = "nodes"
        elif type_name == "element_set": value["preferred_projection"] = "elements"
        elif type_name == "surface": value["preferred_projection"] = "facets"
    if type_name in _LOAD_TYPES | _SUPPORT_TYPES:
        value["target"] = _definition_from_target(value.get("target"))
        if type_name == "concentrated_load": value.setdefault("distribution", "per_node")
    if type_name == "section_assignment":
        value["target"] = _definition_from_target(value.pop("region_ref", None))
    if type_name in _CONSTRAINT_TYPES:
        value.pop("parameters", None)
        master = value.pop("master", None)
        slave = value.pop("slave", None)
        master_definition = _definition_from_constraint_reference(master)
        slave_definition = _definition_from_constraint_reference(slave)
        if type_name in {"kinematic_coupling", "distributing_coupling"}:
            value["control_point"] = master_definition; value["slave"] = slave_definition
            value.pop("adjust", None); value.pop("distance", None)
        elif type_name == "rigid_body_constraint":
            value["reference"] = master_definition; value["body"] = slave_definition
            value.pop("adjust", None); value.pop("distance", None); value.pop("components", None)
        else:
            value["master"] = master_definition; value["slave"] = slave_definition
            if type_name != "tie_constraint":
                value.pop("adjust", None); value.pop("distance", None)
    if type_name == "mesh_state": value.setdefault("revision", "")


def _definition_from_members(values) -> dict[str, Any]:
    return {"__type__": "region_definition", "items": {"__tuple__": [_selection_item(_operand_from_member(item)) for item in values or ()]}}


def _definition_from_target(value) -> dict[str, Any]:
    if isinstance(value, dict) and value.get("__type__") == "region_definition": return value
    if not value: return {"__type__": "region_definition", "items": {"__tuple__": []}}
    type_name = value.get("__type__") if isinstance(value, dict) else ""
    if type_name == "mesh_node_target":
        operand = {"__type__": "mesh_node_operand", "owner_ref": value.get("owner_ref") or _entity_ref("", "Part"), "node_id": value.get("node_id", 0), "instance_ref": None, "mesh_revision": ""}
    elif type_name == "mesh_element_target":
        operand = {"__type__": "mesh_element_operand", "owner_ref": value.get("owner_ref") or _entity_ref("", "Part"), "element_id": value.get("element_id", 0), "instance_ref": None, "mesh_revision": ""}
    elif type_name in {"reference_point_target"}:
        operand = {"__type__": "reference_point_operand", "reference_point_ref": value.get("ref") or _entity_ref("", "ReferencePoint"), "instance_ref": None}
    elif type_name == "whole_model_target":
        operand = {"__type__": "whole_model_operand", "owner_ref": None, "instance_ref": None}
    elif type_name in {"entity_target", "node_set_target", "element_set_target", "surface_target"}:
        operand = {"__type__": "named_region_operand", "region_ref": value.get("ref") or _entity_ref("", "Region"), "instance_ref": None}
    elif isinstance(value, dict) and value.get("__type__") == "entity_ref":
        operand = {"__type__": "named_region_operand", "region_ref": value, "instance_ref": None}
    else:
        operand = {"__type__": "unresolved_operand", "legacy_label": str(value), "expected_kind": ""}
    return {"__type__": "region_definition", "items": {"__tuple__": [_selection_item(operand)]}}


def _definition_from_constraint_reference(value) -> dict[str, Any]:
    if isinstance(value, dict) and value.get("__type__") == "constraint_reference":
        kind = str(value.get("kind") or "")
        ref = value.get("ref") or _entity_ref("", kind.replace(" ", ""))
        if kind == "Reference Point":
            operand = {"__type__": "reference_point_operand", "reference_point_ref": ref, "instance_ref": None}
        else:
            operand = {"__type__": "named_region_operand", "region_ref": ref, "instance_ref": None}
        return {"__type__": "region_definition", "items": {"__tuple__": [_selection_item(operand)]}}
    return _definition_from_target(value)


def _operand_from_member(value) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("__type__") != "region_member_ref":
        return {"__type__": "unresolved_operand", "legacy_label": str(value), "expected_kind": ""}
    kind = str(value.get("kind") or "Unknown")
    owner_ref = value.get("owner_ref") or _entity_ref("", "Part")
    instance_ref = owner_ref if str(owner_ref.get("expected_type", "")) == "Instance" else None
    if kind == "Reference Point":
        return {"__type__": "reference_point_operand", "reference_point_ref": value.get("entity_ref") or _entity_ref("", "ReferencePoint"), "instance_ref": instance_ref}
    if kind == "Node":
        return {"__type__": "mesh_node_operand", "owner_ref": owner_ref, "node_id": value.get("tag", 0), "instance_ref": instance_ref, "mesh_revision": ""}
    if kind == "Element":
        return {"__type__": "mesh_element_operand", "owner_ref": owner_ref, "element_id": value.get("tag", 0), "instance_ref": instance_ref, "mesh_revision": ""}
    dimensions = {"Vertex": 0, "Edge": 1, "Face": 2, "Cell": 3}
    if kind in dimensions:
        return {"__type__": "geometry_operand", "owner_ref": owner_ref, "dimension": dimensions[kind], "tag": value.get("tag", 0), "instance_ref": instance_ref, "topology_revision": ""}
    return {"__type__": "unresolved_operand", "legacy_label": value.get("legacy_label", str(value)), "expected_kind": kind}


def _selection_item(operand) -> dict[str, Any]:
    return {"__type__": "region_selection_item", "operand": operand, "picked_position": None, "display_label": ""}


def _migrate_14_to_15(data: dict[str, Any], report: MigrationReport) -> dict[str, Any]:
    """Move meshing selections to the same generic RegionDefinition model."""
    _walk_14_to_15(data)
    report.changes.extend([
        "Converted edge seeds, mesh controls and element controls to generic region targets",
        "Separated persistent selection definitions from legacy label lists",
    ])
    return data


def _walk_14_to_15(value: Any, owner_ref: dict[str, Any] | None = None) -> None:
    if isinstance(value, list):
        for item in value:
            _walk_14_to_15(item, owner_ref)
        return
    if not isinstance(value, dict):
        return
    type_name = value.get("__type__", "")
    local_owner = owner_ref
    if type_name == "part":
        local_owner = _entity_ref_from_id(value.get("id", ""), "Part")
    for item in list(value.values()):
        _walk_14_to_15(item, local_owner)
    if type_name in {"mesh_seed", "default_seed", "edge_seed", "mesh_control", "free_mesh_control", "structured_mesh_control", "sweep_mesh_control", "element_control"}:
        if "target" not in value:
            value["target"] = _definition_from_legacy_selection(value.pop("targets", ()), local_owner)
        else:
            value.pop("targets", None)


def _definition_from_legacy_selection(values, owner_ref):
    items = []
    for value in values or ():
        operand = _operand_from_legacy_selection(value, owner_ref)
        if operand is not None:
            items.append(_selection_item(operand))
    return {"__type__": "region_definition", "items": {"__tuple__": items}}


def _operand_from_legacy_selection(value, owner_ref):
    if isinstance(value, dict):
        type_name = value.get("__type__", "")
        if type_name == "region_member_ref":
            return _operand_from_member(value)
        if type_name == "entity_ref":
            return {"__type__": "named_region_operand", "region_ref": value, "instance_ref": None}
        if type_name in {"geometry_operand", "mesh_node_operand", "mesh_element_operand", "mesh_facet_operand", "named_region_operand", "reference_point_operand", "whole_model_operand"}:
            return value
    text = str(value or "").strip()
    local = text.split(".")[-1]
    if ":" in local and local.casefold().startswith("elementset:"):
        return {"__type__": "unresolved_operand", "legacy_label": local.split(":", 1)[1], "expected_kind": "Region"}
    import re
    match = re.fullmatch(r"(Vertex|Edge|Face|Cell|Node|Element)-(\d+)", local, re.IGNORECASE)
    if not match:
        return {"__type__": "unresolved_operand", "legacy_label": text, "expected_kind": ""} if text else None
    kind, tag = match.group(1).casefold(), int(match.group(2))
    owner = owner_ref or _entity_ref("", "Part")
    dimensions = {"vertex": 0, "edge": 1, "face": 2, "cell": 3}
    if kind in dimensions:
        return {"__type__": "geometry_operand", "owner_ref": owner, "dimension": dimensions[kind], "tag": tag, "instance_ref": None, "topology_revision": ""}
    if kind == "node":
        return {"__type__": "mesh_node_operand", "owner_ref": owner, "node_id": tag, "instance_ref": None, "mesh_revision": ""}
    return {"__type__": "mesh_element_operand", "owner_ref": owner, "element_id": tag, "instance_ref": None, "mesh_revision": ""}


def _entity_ref_from_id(entity_id: Any, expected: str) -> dict[str, Any]:
    return {"__type__": "entity_ref", "entity_id": str(entity_id or ""), "expected_type": expected, "legacy_name": ""}


def _migrate_15_to_16(data: dict[str, Any], report: MigrationReport) -> dict[str, Any]:
    """Add persistent geometry-face to oriented mesh-facet associations."""
    def walk(value):
        if isinstance(value, list):
            for item in value:
                walk(item)
            return
        if not isinstance(value, dict):
            return
        for item in value.values():
            walk(item)
        if value.get("__type__") == "mesh_state":
            value.setdefault("entity_facets", {})
    walk(data)
    report.changes.append("Added persistent CAD-face to oriented mesh-facet associations")
    return data


def _migrate_16_to_17(data: dict[str, Any], report: MigrationReport) -> dict[str, Any]:
    """Move geometry-history selections to generic RegionDefinition values."""
    _walk_16_to_17(data)
    report.changes.extend([
        "Converted geometry-feature target selections to generic RegionDefinition operands",
        "Converted edge-at-vertex split selections to a dedicated RegionDefinition",
        "Removed the final runtime dependency on RegionMemberRef",
    ])
    return data


def _walk_16_to_17(value: Any, owner_ref: dict[str, Any] | None = None) -> None:
    if isinstance(value, list):
        for item in value: _walk_16_to_17(item, owner_ref)
        return
    if not isinstance(value, dict): return
    type_name = value.get("__type__", "")
    local_owner = owner_ref
    if type_name == "part": local_owner = _entity_ref_from_id(value.get("id", ""), "Part")
    for item in list(value.values()): _walk_16_to_17(item, local_owner)
    if type_name not in _GEOMETRY_FEATURE_TYPES: return
    if "target" not in value:
        value["target"] = _definition_from_legacy_selection(value.pop("references", ()), local_owner)
    else:
        value.pop("references", None)
    parameters = value.get("parameters") if isinstance(value.get("parameters"), dict) else {}
    if type_name == "partition_edge_feature" or value.get("feature_type") == "Partition Edge":
        if "split_target" not in value:
            value["split_target"] = _definition_from_legacy_selection(parameters.pop("vertices", ()), local_owner)
    value["parameters"] = parameters


def _migrate_17_to_18(data: dict[str, Any], report: MigrationReport) -> dict[str, Any]:
    """Promote known geometry-feature settings from an untyped parameter bag."""
    def walk(value):
        if isinstance(value, list):
            for item in value: walk(item)
            return
        if not isinstance(value, dict): return
        for item in list(value.values()): walk(item)
        type_name = value.get("__type__", "")
        if type_name not in _GEOMETRY_FEATURE_TYPES: return
        parameters = value.get("parameters") if isinstance(value.get("parameters"), dict) else {}
        if type_name == "imported_step_feature":
            value.setdefault("source_file", str(parameters.pop("file", "")))
        elif type_name in {"partition_plane_feature", "partition_cell_feature"}:
            value.setdefault("origin", parameters.pop("origin", {"__tuple__": [0.0, 0.0, 0.0]}))
            value.setdefault("normal", parameters.pop("normal", {"__tuple__": [1.0, 0.0, 0.0]}))
            datum_id = parameters.pop("datum_plane_id", "")
            value.setdefault("datum_plane_ref", _entity_ref_from_id(datum_id, "DatumPlane") if datum_id else None)
        elif type_name == "partition_face_feature":
            value.setdefault("points", parameters.pop("points", {"__tuple__": []}))
        elif type_name == "partition_edge_feature":
            value.setdefault("method", parameters.pop("method", "Parameter"))
            value.setdefault("fraction", parameters.pop("fraction", 0.5))
        value["parameters"] = parameters
    walk(data)
    report.changes.extend([
        "Promoted imported geometry source paths to explicit feature fields",
        "Promoted partition plane, face and edge settings to concrete dataclass fields",
        "Replaced geometry-history feature-type parameter switches with class dispatch",
    ])
    return data


def _migrate_18_to_19(data: dict[str, Any], report: MigrationReport) -> dict[str, Any]:
    """Eliminate untyped/mixed named regions from persisted projects."""
    converted = 0

    def walk(value):
        nonlocal converted
        if isinstance(value, list):
            for item in value:
                walk(item)
            return
        if not isinstance(value, dict):
            return
        for item in list(value.values()):
            walk(item)
        if value.get("__type__") == "region" and value.get("preferred_projection") in (None, "", "single_control_node"):
            # Older generic regions had no declared semantic type.  A control
            # point is an inline constraint target, never a named-region type.
            # Keep either legacy form loadable as a strict node region.
            value["preferred_projection"] = "nodes"
            converted += 1

    walk(data)
    report.changes.append(
        f"Converted {converted} untyped region(s) to node regions"
        if converted else
        "Enforced node, element, or surface typing for every region"
    )
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
        _move_ref(value, "region_name", "region_ref", "Region")
        _move_optional_ref(value, "orientation_name", "orientation_ref", "Orientation", ignored={"Global"})

    if type_name == "orientation":
        _move_ref(value, "region_name", "region_ref", "Region")
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
_GEOMETRY_FEATURE_TYPES = {
    "geometry_feature", "imported_step_feature", "partition_cell_feature",
    "partition_edge_feature", "partition_face_feature", "partition_plane_feature",
}

_MIGRATIONS: dict[int, Migration] = {
    POLYMORPHIC_NAME_REFERENCE_VERSION: _migrate_11_to_12,
    12: _migrate_12_to_13,
    13: _migrate_13_to_14,
    14: _migrate_14_to_15,
    15: _migrate_15_to_16,
    16: _migrate_16_to_17,
    17: _migrate_17_to_18,
    18: _migrate_18_to_19,
}
