from __future__ import annotations

from dataclasses import fields, is_dataclass, replace
from typing import Any

from .entity import Entity
from .project_index import ProjectIndex
from .reference import EntityRef


def repair_project_references(project) -> list[str]:
    """Resolve legacy name references exactly once after loading/migration.

    Runtime validation never calls this function and therefore never mutates the
    model. Ambiguous names are reported instead of guessed.
    """
    index = ProjectIndex(project)
    errors: list[str] = []

    def bind(ref: EntityRef, path: str) -> EntityRef:
        if ref.entity_id: return ref
        if not ref.legacy_name: return ref
        candidates = [entity for entity in index.by_id.values() if entity.name.casefold() == ref.legacy_name.casefold() and _expected(entity, ref.expected_type)]
        if len(candidates) == 1: return EntityRef.of(candidates[0], ref.expected_type or type(candidates[0]).__name__)
        if not candidates: errors.append(f"{path}: '{ref.legacy_name}' was not found")
        else: errors.append(f"{path}: '{ref.legacy_name}' is ambiguous ({len(candidates)} matches)")
        return ref

    def rewrite(value: Any, path: str):
        if isinstance(value, EntityRef): return bind(value, path)
        if isinstance(value, Entity):
            for info in fields(value):
                if not info.init: continue
                current = getattr(value, info.name)
                updated = rewrite(current, f"{path}.{info.name}")
                if updated is not current: setattr(value, info.name, updated)
            return value
        if is_dataclass(value):
            changes = {}
            for info in fields(value):
                if not info.init: continue
                current = getattr(value, info.name)
                updated = rewrite(current, f"{path}.{info.name}")
                if updated is not current: changes[info.name] = updated
            return replace(value, **changes) if changes else value
        if isinstance(value, list):
            return [rewrite(item, f"{path}[{index}]") for index, item in enumerate(value)]
        if isinstance(value, tuple):
            return tuple(rewrite(item, f"{path}[{index}]") for index, item in enumerate(value))
        if isinstance(value, dict):
            return {key: rewrite(item, f"{path}[{key!r}]") for key, item in value.items()}
        return value

    rewrite(project, "project")
    return errors


def validate_project_references(project, index: ProjectIndex | None = None, strict: bool = False) -> list[str]:
    index = index or ProjectIndex(project)
    errors: list[str] = []

    def walk(value: Any, path: str):
        if isinstance(value, EntityRef):
            if not value.entity_id:
                if value.legacy_name: errors.append(f"{path}: unresolved legacy reference '{value.legacy_name}'")
                return
            entity = index.by_id.get(value.entity_id)
            if entity is None: errors.append(f"{path}: entity '{value.entity_id}' does not exist")
            elif not _expected(entity, value.expected_type): errors.append(f"{path}: {type(entity).__name__} is not {value.expected_type}")
            return
        if isinstance(value, Entity):
            for info in fields(value):
                if info.name.startswith("_"): continue
                walk(getattr(value, info.name), f"{path}.{info.name}")
            return
        if is_dataclass(value):
            for info in fields(value): walk(getattr(value, info.name), f"{path}.{info.name}")
        elif isinstance(value, (list, tuple)):
            for number, item in enumerate(value): walk(item, f"{path}[{number}]")
        elif isinstance(value, dict):
            for key, item in value.items(): walk(item, f"{path}[{key!r}]")

    walk(project, "project")
    errors.extend(_validate_region_consumers(project))
    if strict and errors: raise ValueError("Invalid model references:\n- " + "\n- ".join(errors))
    return errors


def bind_project_references(project, index=None, strict=False):
    """Compatibility alias; binding no longer occurs during normal mutations."""
    return validate_project_references(project, index, strict)


def _validate_region_consumers(project):
    from opencae.model.entities.constraints import ConstraintType, constraint_region_requirement
    from opencae.model.entities.loads import TemperatureLoad, load_region_requirement
    from opencae.model.entities.supports import SUPPORT_REGION_REQUIREMENT
    from opencae.model.selection import RegionProjection, RegionRequirement, validate_region_definition
    errors = []

    def check(owner, definition, requirement, *, allow_part_local=False):
        diagnostics = validate_region_definition(
            project, definition, requirement, allow_part_local=allow_part_local
        )
        errors.extend(
            f"{type(owner).__name__} {owner.name}: {item.message}"
            for item in diagnostics
            if item.severity == "error"
        )

    for support in project.supports:
        check(support, support.target, SUPPORT_REGION_REQUIREMENT)
    for load in project.loads:
        requirement = load_region_requirement(load)
        if not isinstance(load, TemperatureLoad) and requirement is not None:
            check(load, load.target, requirement)
    for part in project.parts:
        for assignment in part.section_assignments:
            check(
                assignment, assignment.target,
                RegionRequirement(RegionProjection.ELEMENTS, (1, 2, 3), 1),
                allow_part_local=True,
            )
        from opencae.model.selection import local_element_ids, local_geometry_tags
        for seed in part.mesh.seeds:
            if getattr(seed, "seed_type", "") != "Edge": continue
            if not local_geometry_tags(part, seed.target, 1):
                errors.append(f"{type(seed).__name__} {seed.name}: target contains no edges")
        for control in part.mesh.controls:
            dimension = {"Edge": 1, "Face": 2, "Cell": 3}.get(str(getattr(control, "scope", "")))
            if dimension is None: continue
            definition = getattr(control, "target", None)
            if definition is not None and not definition.empty and not local_geometry_tags(part, definition, dimension):
                errors.append(f"{type(control).__name__} {control.name}: target contains no {str(control.scope).lower()} entities")
        for control in part.mesh.element_controls:
            if not control.target.empty and not local_element_ids(part, control.target):
                errors.append(f"{type(control).__name__} {control.name}: target contains no elements")
    for constraint in project.assembly.constraints:
        kind = ConstraintType.coerce(constraint.constraint_type)
        if kind in {ConstraintType.KINEMATIC, ConstraintType.DISTRIBUTING}:
            check(constraint, constraint.control_point, constraint_region_requirement(kind, "master"))
            check(constraint, constraint.slave, constraint_region_requirement(kind, "slave"))
        elif kind == ConstraintType.TIE:
            check(constraint, constraint.master, constraint_region_requirement(kind, "master"))
            check(constraint, constraint.slave, constraint_region_requirement(kind, "slave"))
        elif kind == ConstraintType.RIGID_BODY:
            check(constraint, constraint.reference, constraint_region_requirement(kind, "master"))
            check(constraint, constraint.body, constraint_region_requirement(kind, "slave"))
    return errors


def _expected(entity, expected_type: str) -> bool:
    if not expected_type: return True
    expected = expected_type.casefold().replace(" ", "")
    names = {cls.__name__.casefold().replace(" ", "") for cls in type(entity).mro()}
    if expected in names: return True
    if expected in {"nodeset", "elementset", "surface", "region"}:
        from opencae.model.entities.regions import Region
        return isinstance(entity, Region)
    return False
