from __future__ import annotations

from dataclasses import fields, is_dataclass

from opencae.geometry.section_filter import region_families
from opencae.model.core import EntityRef
from opencae.model.entities.loads import TemperatureLoad
from opencae.model.selection import RegionProjection, RegionRequirement, validate_region_definition


def section_assignment_errors(project):
    project.ensure_references(False)
    errors = []
    for part in project.parts:
        for assignment in part.section_assignments:
            section = project.try_resolve(assignment.section_ref)
            if section is None:
                errors.append(f"{part.name}/{assignment.name}: referenced section does not exist")
                continue
            diagnostics = validate_region_definition(
                project,
                assignment.target,
                RegionRequirement(RegionProjection.ELEMENTS, (1, 2, 3), 1),
                allow_part_local=True,
            )
            errors.extend(
                f"{part.name}/{assignment.name}: {item.message}"
                for item in diagnostics
                if item.severity == "error"
            )
            families = region_families(project, part, assignment.target)
            if families and section.section_type not in families:
                actual = ", ".join(sorted(families))
                errors.append(f"{part.name}/{assignment.name}: {section.section_type} section cannot be assigned to {actual} elements")
    return _unique(errors)


def validate_section_assignments(project):
    errors = section_assignment_errors(project)
    if errors:
        raise ValueError("Invalid section assignments:\n" + "\n".join(errors))


def validate_project(project):
    project.ensure_references(False)
    errors = list(project.reference_errors)
    errors.extend(_reference_errors(project))
    errors.extend(section_assignment_errors(project))
    errors.extend(_region_consumer_errors(project))
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
            if value.expected_type and not _matches_expected(target, value.expected_type):
                errors.append(f"{source.name}.{path}: expected {value.expected_type}, got {type(target).__name__}")
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


def _region_consumer_errors(project):
    # Reference binding already performs the canonical region checks. Keep this
    # entry point for callers of validate_project and add domain-specific fields.
    errors = []
    for load in project.loads:
        if isinstance(load, TemperatureLoad):
            if load.temperature_field_ref is None or project.try_resolve(load.temperature_field_ref) is None:
                errors.append(f"{load.name}: temperature field is missing")
    return errors


def _matches_expected(entity, expected):
    normalized = expected.replace(" ", "").casefold()
    names = {cls.__name__.replace(" ", "").casefold() for cls in type(entity).mro()}
    if normalized in names:
        return True
    aliases = {
        "region": {"region", "nodeset", "elementset", "surface"},
        "nodeset": {"region", "nodeset"},
        "elementset": {"region", "elementset"},
        "surface": {"region", "surface"},
        "load": {"load", "concentratedload", "distributedload", "pressureload", "volumeload", "temperatureload", "inertiaload"},
        "support": {"support", "fixedsupport", "displacementsupport", "symmetrysupport", "remotedisplacementsupport", "temperaturesupport"},
    }
    return bool(names & aliases.get(normalized, set()))


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
