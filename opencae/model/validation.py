from __future__ import annotations

from dataclasses import fields, is_dataclass

from opencae.geometry.section_filter import region_families
from opencae.model.core import EntityRef, EntityTarget, MeshElementTarget, MeshNodeTarget, TargetKind
from opencae.model.entities.loads import ConcentratedLoad, DistributedLoad, InertiaLoad, PressureLoad, TemperatureLoad, VolumeLoad
from opencae.model.entities.supports import Support


def section_assignment_errors(project):
    project.ensure_references(False)
    errors = []
    for part in project.parts:
        for assignment in part.section_assignments:
            section = project.try_resolve(assignment.section_ref)
            region = project.try_resolve(assignment.region_ref)
            if section is None:
                errors.append(f"{part.name}/{assignment.name}: referenced section does not exist")
                continue
            if region is None:
                errors.append(f"{part.name}/{assignment.name}: referenced element set does not exist")
                continue
            families = region_families(part, region)
            if families and section.section_type not in families:
                actual = ", ".join(sorted(families))
                errors.append(f"{part.name}/{assignment.name}: {section.section_type} section cannot be assigned to {actual} elements")
    return errors


def validate_section_assignments(project):
    errors = section_assignment_errors(project)
    if errors:
        raise ValueError("Invalid section assignments:\n" + "\n".join(errors))


def validate_project(project):
    project.ensure_references(False)
    errors = list(project.reference_errors)
    errors.extend(_reference_errors(project))
    errors.extend(section_assignment_errors(project))
    errors.extend(_target_errors(project))
    errors.extend(_step_errors(project))
    return _unique(errors)


def _reference_errors(project):
    errors = []

    def walk(value, source, path):
        if isinstance(value, EntityRef):
            if not value.entity_id:
                if value.legacy_name:
                    errors.append(f"{source.name}.{path}: unresolved reference '{value.legacy_name}'")
                return
            target = project.try_resolve(value)
            if target is None:
                errors.append(f"{source.name}.{path}: target '{value.entity_id}' does not exist")
                return
            expected = value.expected_type
            if expected and not _matches_expected(target, expected):
                errors.append(f"{source.name}.{path}: expected {expected}, got {type(target).__name__}")
            return
        if hasattr(value, "id") and is_dataclass(value):
            return
        if is_dataclass(value):
            for field_info in fields(value):
                walk(getattr(value, field_info.name), source, f"{path}.{field_info.name}" if path else field_info.name)
        elif isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                walk(item, source, f"{path}[{index}]")
        elif isinstance(value, dict):
            for key, item in value.items():
                walk(item, source, f"{path}[{key!r}]")

    for entity in project.index.by_id.values():
        for field_info in fields(entity):
            walk(getattr(entity, field_info.name), entity, field_info.name)
    return errors


def _matches_expected(entity, expected):
    normalized = expected.replace(" ", "").casefold()
    names = {cls.__name__.replace(" ", "").casefold() for cls in type(entity).mro()}
    region_type = str(getattr(entity, "region_type", "")).replace(" ", "").casefold()
    if normalized in {"nodeset", "elementset", "surface", "referencepoint"} and region_type == normalized:
        return True
    aliases = {
        "region": {"nodeset", "elementset", "surface", "referencepoint", "region"},
        "load": {"concentratedload", "distributedload", "pressureload", "volumeload", "temperatureload", "inertiaload", "load"},
        "support": {"fixedsupport", "displacementsupport", "symmetrysupport", "remotedisplacementsupport", "temperaturesupport", "support"},
    }
    return normalized in names or any(name in names for name in aliases.get(normalized, set()))


def _target_errors(project):
    errors = []
    for entity in (*project.loads, *project.supports):
        if isinstance(entity, TemperatureLoad):
            if entity.temperature_field_ref is None or project.try_resolve(entity.temperature_field_ref) is None:
                errors.append(f"{entity.name}: temperature field is missing")
            continue
        target = entity.target
        if target is None:
            errors.append(f"{entity.name}: target is missing")
            continue
        allowed = _allowed_target_kinds(entity)
        if target.kind not in allowed:
            errors.append(f"{entity.name}: {target.kind.value} is not valid for {getattr(entity, 'load_type', getattr(entity, 'support_type', type(entity).__name__))}")
            continue
        if isinstance(target, EntityTarget):
            if target.kind == TargetKind.WHOLE_MODEL:
                continue
            resolved = project.try_resolve(target.ref)
            if resolved is None:
                errors.append(f"{entity.name}: target does not exist")
        elif isinstance(target, (MeshNodeTarget, MeshElementTarget)):
            errors.extend(_mesh_target_errors(project, entity, target))
        else:
            errors.append(f"{entity.name}: unsupported target type {type(target).__name__}")
    return errors


def _allowed_target_kinds(entity):
    if isinstance(entity, Support):
        return {TargetKind.NODE_SET, TargetKind.REFERENCE_POINT, TargetKind.MESH_NODE}
    load_type = str(getattr(entity, "load_type", ""))
    if isinstance(entity, (ConcentratedLoad,)) or load_type in {"Concentrated Load", "Force", "Moment"}:
        return {TargetKind.NODE_SET, TargetKind.REFERENCE_POINT, TargetKind.MESH_NODE}
    if isinstance(entity, (DistributedLoad, PressureLoad)) or load_type in {"Surface Traction", "Pressure"}:
        return {TargetKind.SURFACE}
    if isinstance(entity, VolumeLoad) or load_type == "Volume Load":
        return {TargetKind.ELEMENT_SET, TargetKind.MESH_ELEMENT}
    if isinstance(entity, InertiaLoad) or load_type in {"Inertia Load", "Gravity", "Body load"}:
        return {TargetKind.ELEMENT_SET, TargetKind.MESH_ELEMENT, TargetKind.WHOLE_MODEL}
    return {TargetKind.NODE_SET, TargetKind.REFERENCE_POINT, TargetKind.MESH_NODE}


def _mesh_target_errors(project, source, target):
    from opencae.model.entities.assembly import Instance
    from opencae.model.entities.parts import Part

    owner = project.try_resolve(target.owner_ref)
    if owner is None:
        return [f"{source.name}: direct target owner does not exist"]
    if isinstance(owner, Instance):
        part = project.try_resolve(owner.part_ref, Part)
        if part is None:
            return [f"{source.name}: target instance has no valid part"]
    elif isinstance(owner, Part):
        part = owner
    else:
        return [f"{source.name}: direct target owner must be a Part or Instance"]
    if isinstance(target, MeshNodeTarget):
        if int(target.node_id) not in {int(value) for value in part.mesh.nodes.ids}:
            return [f"{source.name}: node {target.node_id} does not exist in {owner.name}"]
    else:
        element_ids = {int(value) for block in part.mesh.element_blocks for value in block.ids}
        if int(target.element_id) not in element_ids:
            return [f"{source.name}: element {target.element_id} does not exist in {owner.name}"]
    return []

def _step_errors(project):
    errors = []
    for analysis in project.analyses:
        for step in analysis.steps:
            for ref in step.load_refs:
                if project.try_resolve(ref) not in project.loads:
                    errors.append(f"{step.name}: referenced load does not exist")
            for ref in step.support_refs:
                if project.try_resolve(ref) not in project.supports:
                    errors.append(f"{step.name}: referenced support does not exist")
    for job in project.jobs:
        if job.analysis_ref and project.try_resolve(job.analysis_ref) not in project.analyses:
            errors.append(f"{job.name}: referenced analysis does not exist")
    return errors


def _unique(values):
    result = []
    seen = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
