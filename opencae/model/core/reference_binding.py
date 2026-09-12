"""Bind and validate direct object relationships in a Project graph."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any

from .entity import Entity
from .persistent_model_field import (
    is_mesh_reference_field,
    is_owned_model_field,
    is_project_index_field,
    is_reference_model_field,
    mesh_reference_kind,
    reference_type_for_field,
)
from .project_index import ProjectIndex
from .reference import EntityRef
from .reference_type import matches_reference_type


def bind_project_object_references(project, index: ProjectIndex | None = None) -> bool:
    """Replace persistence wire references with canonical runtime objects.

    ``decode_model`` deliberately leaves ``EntityRef`` and compact mesh IDs in
    relationship fields. This pass is the only place where those persistence
    values enter the runtime graph. It also canonicalizes already-object-valued
    mesh references after cloning or mesh editing.
    """
    index = index or ProjectIndex(project)
    changed = False
    active: set[int] = set()

    def bind_entity_reference(value, expected_type: str):
        nonlocal changed
        if value is None:
            return None
        if isinstance(value, list):
            result = [bind_entity_reference(item, expected_type) for item in value]
            changed |= any(a is not b for a, b in zip(result, value, strict=True))
            return result
        if isinstance(value, tuple):
            result = tuple(bind_entity_reference(item, expected_type) for item in value)
            changed |= any(a is not b for a, b in zip(result, value, strict=True))
            return result
        if isinstance(value, dict):
            result = {
                key: bind_entity_reference(item, expected_type)
                for key, item in value.items()
            }
            changed |= any(result[key] is not value[key] for key in value)
            return result
        if isinstance(value, EntityRef):
            if not value.entity_id:
                changed = True
                return None
            resolved = index.try_resolve(value, expected_type or value.expected_type)
            if resolved is None:
                return value
            changed = True
            return resolved
        return value

    def walk(value: Any) -> None:
        nonlocal changed
        if isinstance(value, EntityRef):
            return
        if not is_dataclass(value) and not isinstance(value, (list, tuple, dict)):
            return
        identity = id(value)
        if identity in active:
            return
        active.add(identity)
        try:
            if is_dataclass(value):
                for info in fields(value):
                    if not is_project_index_field(info):
                        continue
                    current = getattr(value, info.name)
                    if is_reference_model_field(info):
                        updated = bind_entity_reference(
                            current,
                            reference_type_for_field(info),
                        )
                        if updated is not current:
                            object.__setattr__(value, info.name, updated)
                    elif is_owned_model_field(info):
                        walk(current)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    walk(item)
            else:
                for item in value.values():
                    walk(item)
        finally:
            active.remove(identity)

    walk(project)

    # Mesh object references depend on the owner relationship being resolved, so
    # canonicalize them in a second traversal.
    active.clear()

    def mesh_object(container, info, current):
        nonlocal changed
        if current is None:
            return None
        kind = mesh_reference_kind(info)
        owner = getattr(container, "owner", None)
        mesh = getattr(owner, "mesh", None)
        if mesh is None:
            return current
        identity = getattr(current, "id", current)
        try:
            canonical = (
                mesh.node(int(identity))
                if kind == "node"
                else mesh.element(int(identity))
            )
        except (KeyError, TypeError, ValueError):
            return current
        if canonical is not current:
            changed = True
        return canonical

    def walk_mesh(value: Any) -> None:
        if isinstance(value, EntityRef):
            return
        if not is_dataclass(value) and not isinstance(value, (list, tuple, dict)):
            return
        identity = id(value)
        if identity in active:
            return
        active.add(identity)
        try:
            if is_dataclass(value):
                for info in fields(value):
                    if not is_project_index_field(info):
                        continue
                    current = getattr(value, info.name)
                    if is_mesh_reference_field(info):
                        updated = mesh_object(value, info, current)
                        if updated is not current:
                            object.__setattr__(value, info.name, updated)
                    elif is_owned_model_field(info):
                        walk_mesh(current)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    walk_mesh(item)
            else:
                for item in value.values():
                    walk_mesh(item)
        finally:
            active.remove(identity)

    walk_mesh(project)
    return changed


def validate_project_references(
    project,
    index: ProjectIndex | None = None,
    strict: bool = False,
) -> list[str]:
    """Validate that every domain relationship points at its canonical object."""
    index = index or ProjectIndex(project)
    errors: list[str] = []
    active: set[int] = set()

    def validate_reference(value, path: str, expected_type: str) -> None:
        if value is None:
            return
        if isinstance(value, (list, tuple)):
            for number, item in enumerate(value):
                validate_reference(item, f"{path}[{number}]", expected_type)
            return
        if isinstance(value, dict):
            for key, item in value.items():
                validate_reference(item, f"{path}[{key!r}]", expected_type)
            return
        if isinstance(value, EntityRef):
            errors.append(
                f"{path}: unresolved persistence reference '{value.entity_id}'"
            )
            return
        if not isinstance(value, Entity):
            errors.append(
                f"{path}: expected {expected_type or 'Entity'} object, "
                f"got {type(value).__name__}"
            )
            return
        canonical = index.by_id.get(value.id)
        if canonical is not value:
            errors.append(
                f"{path}: {type(value).__name__} '{value.name}' does not belong "
                "to this Project as the canonical object"
            )
        elif not matches_reference_type(value, expected_type):
            errors.append(
                f"{path}: {type(value).__name__} is not {expected_type}"
            )

    def validate_mesh_reference(container, info, value, path: str) -> None:
        if value is None:
            return
        owner = getattr(container, "owner", None)
        mesh = getattr(owner, "mesh", None)
        if mesh is None:
            errors.append(f"{path}: mesh reference has no owning Part object")
            return
        kind = mesh_reference_kind(info)
        identity = getattr(value, "id", value)
        try:
            canonical = (
                mesh.node(int(identity))
                if kind == "node"
                else mesh.element(int(identity))
            )
        except (KeyError, TypeError, ValueError):
            errors.append(f"{path}: referenced mesh {kind} does not exist")
            return
        if canonical is not value:
            errors.append(f"{path}: mesh {kind} is not the canonical object")

    def walk(value: Any, path: str) -> None:
        if isinstance(value, EntityRef):
            return
        if not is_dataclass(value) and not isinstance(value, (list, tuple, dict)):
            return
        identity = id(value)
        if identity in active:
            return
        active.add(identity)
        try:
            if is_dataclass(value):
                for info in fields(value):
                    if not is_project_index_field(info):
                        continue
                    child = getattr(value, info.name)
                    child_path = f"{path}.{info.name}"
                    if is_reference_model_field(info):
                        validate_reference(
                            child,
                            child_path,
                            reference_type_for_field(info),
                        )
                    elif is_mesh_reference_field(info):
                        validate_mesh_reference(value, info, child, child_path)
                    elif is_owned_model_field(info):
                        walk(child, child_path)
            elif isinstance(value, (list, tuple)):
                for number, item in enumerate(value):
                    walk(item, f"{path}[{number}]")
            else:
                for key, item in value.items():
                    walk(item, f"{path}[{key!r}]")
        finally:
            active.remove(identity)

    walk(project, "project")
    if strict and errors:
        raise ValueError("Invalid model references:\n- " + "\n- ".join(errors))
    return errors


def validate_region_consumers(project) -> list[str]:
    """Validate region-valued relationships with their consumer requirements."""
    from opencae.model.entities.constraints import (
        ConstraintType,
        constraint_region_requirement,
    )
    from opencae.model.entities.loads import TemperatureLoad, load_region_requirement
    from opencae.model.entities.supports import SUPPORT_REGION_REQUIREMENT
    from opencae.model.selection import (
        RegionProjection,
        RegionRequirement,
        validate_region_definition,
    )

    errors: list[str] = []

    def check(owner, definition, requirement, *, allow_part_local=False):
        diagnostics = validate_region_definition(
            project,
            definition,
            requirement,
            allow_part_local=allow_part_local,
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
                assignment,
                assignment.target,
                RegionRequirement(RegionProjection.ELEMENTS, (1, 2, 3), 1),
                allow_part_local=True,
            )
        from opencae.model.selection import local_element_ids, local_geometry_tags

        for seed in part.mesh.seeds:
            if getattr(seed, "seed_type", "") != "Edge":
                continue
            if not local_geometry_tags(part, seed.target, 1):
                errors.append(
                    f"{type(seed).__name__} {seed.name}: target contains no edges"
                )
        for control in part.mesh.element_controls:
            if not control.target.empty and not local_element_ids(part, control.target):
                errors.append(
                    f"{type(control).__name__} {control.name}: target contains no elements"
                )
    for constraint in project.assembly.constraints:
        kind = ConstraintType.coerce(constraint.constraint_type)
        if kind in {ConstraintType.KINEMATIC, ConstraintType.DISTRIBUTING}:
            check(
                constraint,
                constraint.control_point,
                constraint_region_requirement(kind, "master"),
            )
            check(
                constraint,
                constraint.slave,
                constraint_region_requirement(kind, "slave"),
            )
        elif kind == ConstraintType.TIE:
            check(
                constraint,
                constraint.master,
                constraint_region_requirement(kind, "master"),
            )
            check(
                constraint,
                constraint.slave,
                constraint_region_requirement(kind, "slave"),
            )
        elif kind == ConstraintType.RIGID_BODY:
            check(
                constraint,
                constraint.reference,
                constraint_region_requirement(kind, "master"),
            )
            check(
                constraint,
                constraint.body,
                constraint_region_requirement(kind, "slave"),
            )
        elif kind == ConstraintType.CONNECTOR:
            check(
                constraint,
                constraint.master,
                constraint_region_requirement(kind, "master"),
            )
            check(
                constraint,
                constraint.slave,
                constraint_region_requirement(kind, "slave"),
            )
    return errors
