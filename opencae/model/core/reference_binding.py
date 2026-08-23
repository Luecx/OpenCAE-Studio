"""Validates stable references in the current persistent Project graph."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any

from .entity import Entity
from .persistent_model_field import is_persistent_model_field
from .project_index import ProjectIndex
from .reference import EntityRef
from .reference_type import matches_reference_type


def validate_project_references(
    project,
    index: ProjectIndex | None = None,
    strict: bool = False,
) -> list[str]:
    """Return diagnostics for unresolved or type-incompatible references.

    Validation is read-only and traverses persistent fields only. Legacy name
    binding is intentionally unsupported in the development file format.
    """
    index = index or ProjectIndex(project)
    errors: list[str] = []
    active_values: set[int] = set()

    def walk(value: Any, path: str) -> None:
        """Visit persistent values once per active recursion path."""
        if isinstance(value, EntityRef):
            if not value.entity_id:
                return
            entity = index.by_id.get(value.entity_id)
            if entity is None:
                errors.append(
                    f"{path}: entity '{value.entity_id}' does not exist"
                )
            elif not matches_reference_type(entity, value.expected_type):
                errors.append(
                    f"{path}: {type(entity).__name__} is not "
                    f"{value.expected_type}"
                )
            return

        if not isinstance(value, Entity) and not is_dataclass(value) and not isinstance(
            value,
            (list, tuple, dict),
        ):
            return

        identity = id(value)
        if identity in active_values:
            return
        active_values.add(identity)
        try:
            if isinstance(value, Entity) or is_dataclass(value):
                for info in fields(value):
                    if is_persistent_model_field(info):
                        walk(
                            getattr(value, info.name),
                            f"{path}.{info.name}",
                        )
            elif isinstance(value, (list, tuple)):
                for number, item in enumerate(value):
                    walk(item, f"{path}[{number}]")
            else:
                for key, item in value.items():
                    walk(item, f"{path}[{key!r}]")
        finally:
            active_values.remove(identity)

    walk(project, "project")
    errors.extend(_validate_region_consumers(project))
    if strict and errors:
        raise ValueError("Invalid model references:\n- " + "\n- ".join(errors))
    return errors


def _validate_region_consumers(project) -> list[str]:
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
    return errors
