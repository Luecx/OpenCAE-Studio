from __future__ import annotations

from copy import deepcopy
from dataclasses import fields, is_dataclass, replace

from .entity import Entity
from .persistent_model_field import is_persistent_model_field
from .reference import EntityRef


def entity_with_replaced_references(entity: Entity, old_id: str, new_entity):
    """Return a copied entity with references to *old_id* replaced.

    The source entity itself is never mutated. This makes reference replacement
    suitable for reversible collection commands and safe across undo/redo.
    """
    replacement = EntityRef.of(new_entity)
    clone = deepcopy(entity)
    changed = False
    for info in fields(clone):
        if info.name == "id" or not is_persistent_model_field(info):
            continue
        updated, did_change = _replace_value(getattr(clone, info.name), old_id, replacement)
        if did_change:
            setattr(clone, info.name, updated)
            changed = True
    return clone, changed


def replace_references(project, old_id: str, new_entity) -> int:
    """Replace every persistent reference to *old_id* with *new_entity*.

    Returns the number of entity fields that changed. Contained model entities
    are processed independently through the project index, which avoids
    rebuilding whole object graphs and preserves entity identity.
    """
    replacement = EntityRef.of(new_entity)
    changed = 0
    for entity in tuple(project.index.by_id.values()):
        for info in fields(entity):
            if info.name == "id" or not is_persistent_model_field(info):
                continue
            value = getattr(entity, info.name)
            updated, did_change = _replace_value(value, old_id, replacement)
            if did_change:
                setattr(entity, info.name, updated)
                changed += 1
    project.rebuild_index()
    return changed


def remap_entity_graph(root: Entity, id_map: dict[str, str]) -> Entity:
    """Apply a precomputed ID map to a copied entity graph in-place."""
    entities = list(_entities_in(root))
    for entity in entities:
        old_id = entity.id
        if old_id in id_map:
            object.__setattr__(entity, "id", id_map[old_id])
    for entity in entities:
        for info in fields(entity):
            if info.name == "id" or not is_persistent_model_field(info):
                continue
            value = getattr(entity, info.name)
            updated, changed = _remap_value(value, id_map)
            if changed:
                setattr(entity, info.name, updated)
        object.__setattr__(entity, "_project", None)
    return root


def clone_entity_graph(root: Entity):
    from opencae.core.ids import new_id

    clone = deepcopy(root)
    ids = [entity.id for entity in _entities_in(clone)]
    return remap_entity_graph(clone, {entity_id: new_id("entity") for entity_id in ids})


def _entities_in(root):
    """Yield every Entity reachable through persistent model fields."""
    seen = set()

    def walk(value):
        if isinstance(value, Entity):
            if id(value) in seen:
                return
            seen.add(id(value))
            yield value
            for info in fields(value):
                if not is_persistent_model_field(info):
                    continue
                yield from walk(getattr(value, info.name))
            return
        if is_dataclass(value):
            if id(value) in seen:
                return
            seen.add(id(value))
            for info in fields(value):
                if not is_persistent_model_field(info):
                    continue
                yield from walk(getattr(value, info.name))
        elif isinstance(value, (list, tuple)):
            if id(value) in seen:
                return
            seen.add(id(value))
            for item in value:
                yield from walk(item)
        elif isinstance(value, dict):
            if id(value) in seen:
                return
            seen.add(id(value))
            for item in value.values():
                yield from walk(item)

    yield from walk(root)


def remove_entity(project, entity_id: str) -> bool:
    """Remove an entity from its owning mutable collection.

    Entity collections can be nested in value dataclasses such as ``MeshState``;
    traversal therefore follows every persistent dataclass field rather than
    only direct Entity children. Direct singleton fields (notably
    ``Project.assembly``) are not deleted implicitly.
    """
    target = project.try_resolve(entity_id)
    if target is None or target is project:
        return False

    def visit(owner):
        if not is_dataclass(owner):
            return False
        for info in fields(owner):
            if not is_persistent_model_field(info):
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
    """Return root plus all externally dependent entities and descendants."""
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
    # Removing ancestors removes their descendants automatically. Remove the
    # shallowest entities first and ignore IDs already gone.
    ordered = sorted(ids, key=lambda value: project.index.path.get(value, "").count("."))
    removed = set()
    for entity_id in ordered:
        if project.try_resolve(entity_id) is not None and remove_entity(project, entity_id):
            removed.add(entity_id)
    project.rebuild_index()
    return removed


def compatible_replacements(project, entity):
    """Return replacements compatible with every incoming typed reference."""
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
    from opencae.model.entities.regions import CoordinateSystem, Orientation, ReferencePoint, Region
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

    # These are polymorphic resource families. A ForceLoad may be replaced by
    # a PressureLoad only when every incoming reference accepts ``Load``; the
    # expected-type check in ``compatible_replacements`` enforces that detail.
    families = (Load, Support, Profile, Analysis, Constraint, Job, ResultSet)
    for family in families:
        if isinstance(entity, family):
            return isinstance(candidate, family)

    # Part/assembly-local entities must never jump ownership scopes. This is
    # what prevents an RP or coordinate system in Part A from being silently
    # replaced by a same-named object in Part B.
    local_families = (ReferencePoint, CoordinateSystem, Orientation)
    if isinstance(entity, local_families):
        return isinstance(candidate, type(entity)) and project.index.parent_id.get(candidate.id) == parent_id

    if parent_id is not None and project.index.parent_id.get(candidate.id) != parent_id:
        root_collections = {project.id, getattr(project.assembly, "id", "")}
        if parent_id not in root_collections:
            return False
    return isinstance(candidate, type(entity)) or isinstance(entity, type(candidate))


def _matches_expected(entity, expected):
    from opencae.model.entities.regions import ReferencePoint, Region
    from opencae.model.selection import RegionProjection

    normalized = str(expected).replace(" ", "").casefold()
    names = {cls.__name__.replace(" ", "").casefold() for cls in type(entity).mro()}
    if normalized == "referencepoint": return isinstance(entity, ReferencePoint)
    projections = {
        "nodeset": RegionProjection.NODES,
        "elementset": RegionProjection.ELEMENTS,
        "surface": RegionProjection.FACETS,
    }
    if normalized in projections:
        return isinstance(entity, Region) and entity.preferred_projection == projections[normalized]
    if normalized == "region": return isinstance(entity, Region)
    aliases = {
        "load": {"load"},
        "support": {"support"},
        "section": {"section"},
        "profile": {"profile"},
        "analysis": {"analysis"},
    }
    return normalized in names or any(name in names for name in aliases.get(normalized, set()))


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


def _replace_value(value, old_id, replacement):
    if isinstance(value, EntityRef):
        if value.entity_id != old_id:
            return value, False
        return EntityRef(replacement.entity_id, value.expected_type or replacement.expected_type), True
    if isinstance(value, Entity):
        return value, False
    if is_dataclass(value):
        changes = {}
        for info in fields(value):
            if not is_persistent_model_field(info):
                continue
            updated, changed = _replace_value(getattr(value, info.name), old_id, replacement)
            if changed:
                changes[info.name] = updated
        return (replace(value, **changes), True) if changes else (value, False)
    if isinstance(value, list):
        result = []
        changed = False
        for item in value:
            updated, item_changed = _replace_value(item, old_id, replacement)
            result.append(updated)
            changed |= item_changed
        return (result, True) if changed else (value, False)
    if isinstance(value, tuple):
        result = []
        changed = False
        for item in value:
            updated, item_changed = _replace_value(item, old_id, replacement)
            result.append(updated)
            changed |= item_changed
        return (tuple(result), True) if changed else (value, False)
    if isinstance(value, dict):
        result = {}
        changed = False
        for key, item in value.items():
            updated, item_changed = _replace_value(item, old_id, replacement)
            result[key] = updated
            changed |= item_changed
        return (result, True) if changed else (value, False)
    return value, False


def _remap_value(value, id_map):
    if isinstance(value, EntityRef):
        mapped = id_map.get(value.entity_id)
        return (EntityRef(mapped, value.expected_type), True) if mapped else (value, False)
    if isinstance(value, Entity):
        return value, False
    if is_dataclass(value):
        changes = {}
        for info in fields(value):
            if not is_persistent_model_field(info):
                continue
            updated, changed = _remap_value(getattr(value, info.name), id_map)
            if changed:
                changes[info.name] = updated
        return (replace(value, **changes), True) if changes else (value, False)
    if isinstance(value, list):
        result, changed = [], False
        for item in value:
            updated, item_changed = _remap_value(item, id_map)
            result.append(updated)
            changed |= item_changed
        return (result, True) if changed else (value, False)
    if isinstance(value, tuple):
        result, changed = [], False
        for item in value:
            updated, item_changed = _remap_value(item, id_map)
            result.append(updated)
            changed |= item_changed
        return (tuple(result), True) if changed else (value, False)
    if isinstance(value, dict):
        result, changed = {}, False
        for key, item in value.items():
            updated, item_changed = _remap_value(item, id_map)
            result[key] = updated
            changed |= item_changed
        return (result, True) if changed else (value, False)
    return value, False
