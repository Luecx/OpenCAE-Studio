from __future__ import annotations

from .project_index import ProjectIndex
from .reference import EntityRef, EntityTarget, TargetKind, entity_target, target_for_entity
from .region_member import bind_region_member


def bind_project_references(project, index: ProjectIndex, strict: bool = False) -> list[str]:
    from opencae.model.entities.constraints import ConstraintReference, ConstraintReferenceKind
    from opencae.model.entities.loads import TemperatureLoad

    errors: list[str] = []

    def bind(ref: EntityRef | None, candidates, path: str, expected="", groups=()):
        if ref is None:
            return None
        candidates = tuple(candidates)
        if ref.entity_id:
            entity = index.by_id.get(ref.entity_id)
            if entity is None:
                errors.append(f"{path}: referenced entity '{ref.entity_id}' does not exist")
                return ref
            if candidates and entity.id not in {item.id for item in candidates}:
                errors.append(f"{path}: '{entity.name}' has an invalid type or scope")
                return ref
            return EntityRef(entity.id, expected or ref.expected_type or type(entity).__name__)
        name = ref.legacy_name
        if not name:
            return EntityRef(expected_type=expected or ref.expected_type)
        search_groups = tuple(tuple(group) for group in groups if group) or (candidates,)
        for group in search_groups:
            matches = _matches(name, group)
            if len(matches) == 1:
                entity = matches[0]
                return EntityRef(entity.id, expected or ref.expected_type or type(entity).__name__)
            if len(matches) > 1:
                errors.append(f"{path}: '{name}' is ambiguous ({', '.join(item.name for item in matches)})")
                return ref
        errors.append(f"{path}: '{name}' was not found")
        return ref

    def bind_target(target, path: str, expected_kind: TargetKind):
        if target is None or not isinstance(target, EntityTarget):
            return target
        target_kind = target.kind if target.kind != TargetKind.UNKNOWN else expected_kind
        if target_kind == TargetKind.WHOLE_MODEL:
            return target
        assembly_candidates, part_candidates = _target_candidate_groups(project, target_kind)
        candidates = (*assembly_candidates, *part_candidates)
        ref = bind(target.ref, candidates, path, target_kind.value.replace(" ", ""), (assembly_candidates, part_candidates))
        entity = index.try_resolve(ref)
        return entity_target(ref, target_for_entity(entity).kind if entity else target_kind)

    parts = tuple(project.parts)
    materials = tuple(project.materials)
    profiles = tuple(project.profiles)
    sections = tuple(project.sections)
    analyses = tuple(project.analyses)
    loads = tuple(project.loads)
    supports = tuple(project.supports)
    jobs = tuple(project.jobs)
    fields = tuple(project.fields)
    assembly_regions = tuple((*project.assembly.node_sets, *project.assembly.element_sets, *project.assembly.surfaces, *project.assembly.reference_points))
    part_regions = tuple(item for part in parts for item in (*part.node_sets, *part.element_sets, *part.surfaces, *part.reference_points))
    all_regions = (*assembly_regions, *part_regions)
    all_csys = tuple((*project.assembly.coordinate_systems, *(item for part in parts for item in part.coordinate_systems)))

    for instance in project.assembly.instances:
        instance.part_ref = bind(instance.part_ref, parts, f"Instance {instance.name}.part_ref", "Part")

    def bind_region_members(owner, regions, owner_label):
        for region in regions:
            bound = []
            for index_number, member in enumerate(region.members):
                value, error = bind_region_member(project, index, member, owner)
                bound.append(value)
                if error:
                    errors.append(f"{owner_label}/{region.name}.members[{index_number}]: {error}")
            region.members = bound

    def bind_local_targets(part, values, path, allow_element_sets=False):
        bound = []
        for index_number, value in enumerate(values or ()):
            if isinstance(value, EntityRef):
                ref = bind(value, part.element_sets, f"{path}[{index_number}]", "ElementSet")
                bound.append(ref)
                continue
            if allow_element_sets and isinstance(value, str) and value.casefold().startswith("elementset:"):
                name = value.split(":", 1)[1].strip()
                ref = bind(EntityRef(expected_type="ElementSet", legacy_name=name), part.element_sets, f"{path}[{index_number}]", "ElementSet")
                bound.append(ref)
                continue
            member, error = bind_region_member(project, index, value, part)
            bound.append(member)
            if error:
                errors.append(f"{path}[{index_number}]: {error}")
        return bound

    for part in parts:
        bind_region_members(part, (*part.node_sets, *part.element_sets, *part.surfaces), part.name)
        for feature in part.geometry:
            feature.references = bind_local_targets(part, feature.references, f"{part.name}/{feature.name}.references")
            vertices = feature.parameters.get("vertices") if isinstance(feature.parameters, dict) else None
            if isinstance(vertices, (list, tuple)):
                feature.parameters["vertices"] = bind_local_targets(part, vertices, f"{part.name}/{feature.name}.parameters.vertices")
        for seed in part.mesh.seeds:
            seed.targets = bind_local_targets(part, seed.targets, f"{part.name}/{seed.name}.targets")
        for control in part.mesh.controls:
            control.targets = bind_local_targets(part, control.targets, f"{part.name}/{control.name}.targets")
        for control in part.mesh.element_controls:
            control.targets = bind_local_targets(
                part, control.targets, f"{part.name}/{control.name}.targets", allow_element_sets=True,
            )
    bind_region_members(
        project.assembly,
        (*project.assembly.node_sets, *project.assembly.element_sets, *project.assembly.surfaces),
        project.assembly.name,
    )

    for section in sections:
        section.material_ref = bind(section.material_ref, materials, f"Section {section.name}.material_ref", "Material") if section.material_ref else None
        section.profile_ref = bind(section.profile_ref, profiles, f"Section {section.name}.profile_ref", "Profile") if section.profile_ref else None

    for part in parts:
        for assignment in part.section_assignments:
            assignment.section_ref = bind(assignment.section_ref, sections, f"{part.name}/{assignment.name}.section_ref", "Section")
            assignment.region_ref = bind(assignment.region_ref, part.element_sets, f"{part.name}/{assignment.name}.region_ref", "ElementSet")
            assignment.orientation_ref = bind(assignment.orientation_ref, part.orientations, f"{part.name}/{assignment.name}.orientation_ref", "Orientation") if assignment.orientation_ref else None
        for orientation in part.orientations:
            orientation.region_ref = bind(orientation.region_ref, part.element_sets, f"{part.name}/{orientation.name}.region_ref", "ElementSet")
            orientation.coordinate_system_ref = bind(orientation.coordinate_system_ref, (*part.coordinate_systems, *project.assembly.coordinate_systems), f"{part.name}/{orientation.name}.coordinate_system_ref", "CoordinateSystem") if orientation.coordinate_system_ref else None

    for field in fields:
        if field.region_ref:
            field.region_ref = bind(field.region_ref, all_regions, f"Field {field.name}.region_ref", "Region", (assembly_regions, part_regions))

    for value in (*supports, *loads):
        kind = _target_kind(value)
        value.target = bind_target(value.target, f"{type(value).__name__} {value.name}.target", kind)
        value.coordinate_system_ref = bind(value.coordinate_system_ref, all_csys, f"{type(value).__name__} {value.name}.coordinate_system_ref", "CoordinateSystem") if value.coordinate_system_ref else None
        if isinstance(value, TemperatureLoad):
            value.temperature_field_ref = bind(value.temperature_field_ref, fields, f"TemperatureLoad {value.name}.temperature_field_ref", "FieldDefinition") if value.temperature_field_ref else None

    assembly_rps = tuple(project.assembly.reference_points)
    part_rps = tuple(item for part in parts for item in part.reference_points)
    for constraint in project.assembly.constraints:
        master_ref = bind(constraint.master.ref, (*assembly_rps, *part_rps), f"Constraint {constraint.name}.master", "ReferencePoint", (assembly_rps, part_rps))
        constraint.master = ConstraintReference(ConstraintReferenceKind.REFERENCE_POINT, master_ref)
        assembly_slaves, part_slaves = _constraint_candidate_groups(project, constraint.slave.kind)
        slave_ref = bind(constraint.slave.ref, (*assembly_slaves, *part_slaves), f"Constraint {constraint.name}.slave", constraint.slave.kind.value.replace(" ", ""), (assembly_slaves, part_slaves))
        constraint.slave = ConstraintReference(constraint.slave.kind, slave_ref)

    for analysis in analyses:
        for step in analysis.steps:
            step.load_refs = [bind(ref, loads, f"Step {step.name}.load_refs", "Load") for ref in step.load_refs]
            step.support_refs = [bind(ref, supports, f"Step {step.name}.support_refs", "Support") for ref in step.support_refs]

    for job in jobs:
        job.analysis_ref = bind(job.analysis_ref, analyses, f"Job {job.name}.analysis_ref", "Analysis") if job.analysis_ref else None
    for result in project.results:
        result.job_ref = bind(result.job_ref, jobs, f"Result {result.name}.job_ref", "Job") if result.job_ref else None

    if strict and errors:
        raise ValueError("Invalid model references:\n- " + "\n- ".join(errors))
    return errors


def _resolved_name(index, ref):
    entity = index.try_resolve(ref)
    return entity.name if entity else (ref.legacy_name if ref else "")


def _matches(name: str, candidates):
    text = str(name).strip()
    folded = text.casefold()
    exact = [item for item in candidates if item.name.casefold() == folded]
    if exact:
        return exact
    suffix = text.replace("/", ".").split(".")[-1].casefold()
    return [item for item in candidates if item.name.casefold() == suffix]


def _target_kind(value):
    load_type = getattr(value, "load_type", "")
    if load_type in {"Pressure", "Surface Traction"}:
        return TargetKind.SURFACE
    if load_type in {"Volume Load", "Inertia Load", "Gravity", "Body load"}:
        return TargetKind.ELEMENT_SET
    return TargetKind.NODE_SET


def _target_candidate_groups(project, kind):
    if kind == TargetKind.SURFACE:
        return tuple(project.assembly.surfaces), tuple(item for part in project.parts for item in part.surfaces)
    if kind == TargetKind.ELEMENT_SET:
        return tuple(project.assembly.element_sets), tuple(item for part in project.parts for item in part.element_sets)
    if kind == TargetKind.REFERENCE_POINT:
        return tuple(project.assembly.reference_points), tuple(item for part in project.parts for item in part.reference_points)
    return (
        tuple((*project.assembly.node_sets, *project.assembly.reference_points)),
        tuple(item for part in project.parts for item in (*part.node_sets, *part.reference_points)),
    )


def _constraint_candidate_groups(project, kind):
    from opencae.model.entities.constraints import ConstraintReferenceKind
    if kind == ConstraintReferenceKind.SURFACE:
        return _target_candidate_groups(project, TargetKind.SURFACE)
    if kind == ConstraintReferenceKind.ELEMENT_SET:
        return _target_candidate_groups(project, TargetKind.ELEMENT_SET)
    if kind == ConstraintReferenceKind.REFERENCE_POINT:
        return _target_candidate_groups(project, TargetKind.REFERENCE_POINT)
    return _target_candidate_groups(project, TargetKind.NODE_SET)
