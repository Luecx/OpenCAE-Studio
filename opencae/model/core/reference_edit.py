from __future__ import annotations

from copy import deepcopy
from dataclasses import fields, is_dataclass

from .entity import Entity
from .persistent_model_field import (
    is_mesh_reference_field,
    is_owned_model_field,
    is_project_index_field,
    is_reference_model_field,
)
from .reference import EntityRef


def entity_with_replaced_references(entity: Entity, old_id: str, new_entity):
    """Return a detached copy with direct references to ``old_id`` rewired."""
    clone = deepcopy(entity, _external_reference_memo(entity))
    changed = _replace_references_in_owned_value(clone, str(old_id), new_entity)
    return clone, changed


def replace_references(project, old_id: str, new_entity) -> int:
    """Replace every direct relationship to one Entity in-place."""
    changed = 0
    for entity in tuple(project.index.by_id.values()):
        if _replace_references_in_owned_value(entity, str(old_id), new_entity):
            changed += 1
    project.rebuild_index()
    return changed


def remap_entity_graph(root: Entity, id_map: dict[str, str]) -> Entity:
    """Apply new identities to owned Entities; object relationships follow them."""
    entities = list(_entities_in(root))
    for entity in entities:
        old_id = entity.id
        if old_id in id_map:
            object.__setattr__(entity, "id", id_map[old_id])
    _remap_wire_references(root, id_map)
    for entity in entities:
        object.__setattr__(entity, "_project", None)
    return root


def clone_entity_graph(root: Entity):
    """Clone an ownership graph while preserving external object relationships.

    References to entities owned inside ``root`` are cloned and continue to point
    at their corresponding clones. References outside ``root`` retain the exact
    canonical target object. This is the object-graph equivalent of remapping
    internal EntityRefs without ever putting IDs into domain fields.
    """
    from opencae.core.ids import new_id

    clone = deepcopy(root, _external_reference_memo(root))
    ids = [entity.id for entity in _entities_in(clone)]
    return remap_entity_graph(
        clone,
        {entity_id: new_id("entity") for entity_id in ids},
    )


def _entities_in(root):
    """Yield every Entity structurally owned through persistent owned fields."""
    seen = set()

    def walk(value):
        if isinstance(value, Entity):
            identity = id(value)
            if identity in seen:
                return
            seen.add(identity)
            yield value
            for info in fields(value):
                if is_owned_model_field(info):
                    yield from walk(getattr(value, info.name))
            return
        if is_dataclass(value):
            identity = id(value)
            if identity in seen:
                return
            seen.add(identity)
            for info in fields(value):
                if is_owned_model_field(info):
                    yield from walk(getattr(value, info.name))
        elif isinstance(value, (list, tuple)):
            identity = id(value)
            if identity in seen:
                return
            seen.add(identity)
            for item in value:
                yield from walk(item)
        elif isinstance(value, dict):
            identity = id(value)
            if identity in seen:
                return
            seen.add(identity)
            for item in value.values():
                yield from walk(item)

    yield from walk(root)


def _external_reference_memo(root: Entity) -> dict[int, object]:
    """Build deepcopy memo entries for references outside one ownership graph."""
    owned = tuple(_entities_in(root))
    owned_objects = {id(entity) for entity in owned}
    memo: dict[int, object] = {}
    seen: set[int] = set()

    def remember_reference(value):
        if value is None:
            return
        if isinstance(value, Entity):
            if id(value) not in owned_objects:
                memo[id(value)] = value
            return
        if isinstance(value, (list, tuple)):
            for item in value:
                remember_reference(item)
            return
        if isinstance(value, dict):
            for item in value.values():
                remember_reference(item)
            return
        # Node/Element are non-Entity dataclass value objects but mesh reference
        # fields intentionally use their runtime identity as the relationship.
        if is_dataclass(value):
            memo[id(value)] = value

    def walk(value):
        if not is_dataclass(value) and not isinstance(value, (list, tuple, dict)):
            return
        identity = id(value)
        if identity in seen:
            return
        seen.add(identity)
        if is_dataclass(value):
            for info in fields(value):
                if not is_project_index_field(info):
                    continue
                item = getattr(value, info.name)
                if is_reference_model_field(info) or is_mesh_reference_field(info):
                    remember_reference(item)
                elif is_owned_model_field(info):
                    walk(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                walk(item)
        else:
            for item in value.values():
                walk(item)

    walk(root)
    return memo


def _replace_references_in_owned_value(value, old_id: str, replacement) -> bool:
    """Rewire only relationship fields while recursively following ownership."""
    changed = False
    active: set[int] = set()

    def replace_relation(item):
        nonlocal changed
        if item is None:
            return item
        if isinstance(item, Entity):
            if item.id == old_id:
                changed = True
                return replacement
            return item
        if isinstance(item, EntityRef):
            if item.entity_id == old_id:
                changed = True
                return EntityRef.of(replacement, item.expected_type)
            return item
        if isinstance(item, list):
            return [replace_relation(child) for child in item]
        if isinstance(item, tuple):
            return tuple(replace_relation(child) for child in item)
        if isinstance(item, dict):
            return {key: replace_relation(child) for key, child in item.items()}
        return item

    def walk(item):
        if not is_dataclass(item) and not isinstance(item, (list, tuple, dict)):
            return
        identity = id(item)
        if identity in active:
            return
        active.add(identity)
        try:
            if is_dataclass(item):
                for info in fields(item):
                    if not is_project_index_field(info):
                        continue
                    current = getattr(item, info.name)
                    if is_reference_model_field(info):
                        updated = replace_relation(current)
                        if updated is not current:
                            object.__setattr__(item, info.name, updated)
                    elif is_owned_model_field(info):
                        walk(current)
            elif isinstance(item, (list, tuple)):
                for child in item:
                    walk(child)
            else:
                for child in item.values():
                    walk(child)
        finally:
            active.remove(identity)

    walk(value)
    return changed


def _remap_wire_references(value, id_map: dict[str, str]) -> None:
    """Remap only unresolved persistence placeholders if they are encountered."""
    active: set[int] = set()

    def remap_relation(item):
        if isinstance(item, EntityRef):
            mapped = id_map.get(item.entity_id)
            return EntityRef(mapped, item.expected_type) if mapped else item
        if isinstance(item, list):
            return [remap_relation(child) for child in item]
        if isinstance(item, tuple):
            return tuple(remap_relation(child) for child in item)
        if isinstance(item, dict):
            return {key: remap_relation(child) for key, child in item.items()}
        return item

    def walk(item):
        if not is_dataclass(item) and not isinstance(item, (list, tuple, dict)):
            return
        identity = id(item)
        if identity in active:
            return
        active.add(identity)
        try:
            if is_dataclass(item):
                for info in fields(item):
                    if not is_project_index_field(info):
                        continue
                    current = getattr(item, info.name)
                    if is_reference_model_field(info):
                        updated = remap_relation(current)
                        if updated is not current:
                            object.__setattr__(item, info.name, updated)
                    elif is_owned_model_field(info):
                        walk(current)
            elif isinstance(item, (list, tuple)):
                for child in item:
                    walk(child)
            else:
                for child in item.values():
                    walk(child)
        finally:
            active.remove(identity)

    walk(value)


def remove_entity(project, entity_id: str) -> bool:
    """Remove an Entity only from its structural owner collection."""
    target = project.try_resolve(entity_id)
    if target is None or target is project:
        return False

    def visit(owner):
        if not is_dataclass(owner):
            return False
        for info in fields(owner):
            if not is_owned_model_field(info):
                continue
            value = getattr(owner, info.name)
            if isinstance(value, list):
                for index, item in enumerate(tuple(value)):
                    if isinstance(item, Entity) and item.id == entity_id:
                        del value[index]
                        return True
                    if is_dataclass(item) and visit(item):
                        return True
            elif isinstance(value, dict):
                for key, item in tuple(value.items()):
                    if isinstance(item, Entity) and item.id == entity_id:
                        del value[key]
                        return True
                    if is_dataclass(item) and visit(item):
                        return True
            elif is_dataclass(value) and value is not target and visit(value):
                return True
        return False

    removed = visit(project)
    if removed:
        project.rebuild_index()
    return removed


def cascade_entity_ids(project, root_id: str) -> set[str]:
    result = _descendant_ids(project, root_id)
    queue = list(result)
    while queue:
        target_id = queue.pop()
        for use in project.references_to(target_id):
            if use.source_id in result:
                continue
            additions = _descendant_ids(project, use.source_id)
            result.update(additions)
            queue.extend(additions)
    return result


def delete_entity_graph(project, root_id: str) -> set[str]:
    ids = cascade_entity_ids(project, root_id)
    ordered = sorted(
        ids,
        key=lambda value: project.index.path.get(value, "").count("."),
    )
    removed = set()
    for entity_id in ordered:
        if (
            project.try_resolve(entity_id) is not None
            and remove_entity(project, entity_id)
        ):
            removed.add(entity_id)
    project.rebuild_index()
    return removed


def compatible_replacements(project, entity):
    uses = project.references_to(entity.id)
    parent_id = project.index.parent_id.get(entity.id)
    result = []
    for candidate in project.index.by_id.values():
        if candidate.id == entity.id or candidate is project:
            continue
        if not _same_semantic_scope(project, entity, candidate, parent_id):
            continue
        expected = {use.expected_type for use in uses if use.expected_type}
        if expected and not all(_matches_expected(candidate, value) for value in expected):
            continue
        result.append(candidate)
    return result


def _same_semantic_scope(project, entity, candidate, parent_id):
    from opencae.model.entities.analysis import Analysis
    from opencae.model.entities.constraints import Constraint
    from opencae.model.entities.jobs import Job, ResultSet
    from opencae.model.entities.loads import Load
    from opencae.model.entities.profiles import Profile
    from opencae.model.entities.regions import (
        CoordinateSystem,
        Orientation,
        ReferencePoint,
        Region,
    )
    from opencae.model.entities.sections import Section
    from opencae.model.entities.supports import Support

    if isinstance(entity, Region):
        return (
            isinstance(candidate, Region)
            and candidate.preferred_projection == entity.preferred_projection
            and project.index.parent_id.get(candidate.id) == parent_id
        )
    if isinstance(entity, Section):
        return isinstance(candidate, Section) and candidate.section_type == entity.section_type

    families = (Load, Support, Profile, Analysis, Constraint, Job, ResultSet)
    for family in families:
        if isinstance(entity, family):
            return isinstance(candidate, family)

    local_families = (ReferencePoint, CoordinateSystem, Orientation)
    if isinstance(entity, local_families):
        return (
            isinstance(candidate, type(entity))
            and project.index.parent_id.get(candidate.id) == parent_id
        )

    if parent_id is not None and project.index.parent_id.get(candidate.id) != parent_id:
        root_collections = {project.id, getattr(project.assembly, "id", "")}
        if parent_id not in root_collections:
            return False
    return isinstance(candidate, type(entity)) or isinstance(entity, type(candidate))


def _matches_expected(entity, expected):
    from opencae.model.entities.regions import ReferencePoint, Region
    from opencae.model.selection import RegionProjection

    options = [item.strip() for item in str(expected).split("|") if item.strip()]
    if len(options) > 1:
        return any(_matches_expected(entity, item) for item in options)
    normalized = str(expected).replace(" ", "").casefold()
    names = {
        cls.__name__.replace(" ", "").casefold()
        for cls in type(entity).mro()
    }
    if normalized == "referencepoint":
        return isinstance(entity, ReferencePoint)
    projections = {
        "nodeset": RegionProjection.NODES,
        "elementset": RegionProjection.ELEMENTS,
        "surface": RegionProjection.FACETS,
    }
    if normalized in projections:
        return (
            isinstance(entity, Region)
            and entity.preferred_projection == projections[normalized]
        )
    if normalized == "region":
        return isinstance(entity, Region)
    aliases = {
        "load": {"load"},
        "support": {"support"},
        "section": {"section"},
        "profile": {"profile"},
        "analysis": {"analysis"},
        "study": {"study"},
        "entity": {"entity"},
    }
    return normalized in names or any(
        name in names for name in aliases.get(normalized, set())
    )


def _descendant_ids(project, entity_id):
    result = {entity_id}
    queue = [entity_id]
    while queue:
        parent_id = queue.pop()
        for child in project.index.children_of(parent_id):
            if child.id not in result:
                result.add(child.id)
                queue.append(child.id)
    return result
