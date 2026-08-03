from __future__ import annotations


def begin_reference_pick(viewport, candidates, allowed, done) -> None:
    """Pick a viewport entity and resolve it to one existing model object."""
    candidates = tuple(candidates)
    project = viewport.store.project

    def selected(entity):
        matches = _matches(entity, candidates, project)
        if len(matches) == 1:
            done(matches[0])
            return
        if not matches:
            viewport.message.emit("The picked viewport entity is not contained in an available reference")
        else:
            viewport.message.emit("The picked viewport entity belongs to multiple references; select one from the list")

    viewport.begin_context_pick(allowed, selected)


def begin_target_pick(
    project,
    viewport,
    candidates,
    allowed,
    done,
    *,
    destination_kind=None,
    default_owner=None,
    mesh_nodes=False,
    mesh_elements=False,
) -> None:
    """Pick an existing target or persist the picked geometry/mesh member directly."""
    candidates = tuple(candidates)

    def selected(entity):
        if destination_kind is not None:
            from opencae.model.core import target_from_selection, target_option
            target = target_from_selection(project, entity, destination_kind, default_owner)
            if target is not None:
                done(target_option(project, target))
                return

        kind = str(entity.get("kind") or entity.get("mesh_entity") or "").lower()
        if mesh_nodes and kind == "node":
            target = _mesh_target(project, entity, node=True)
            if target is not None:
                done((entity.get("name", f"Node-{entity.get('tag')}"), target))
                return
        if mesh_elements and kind == "element":
            target = _mesh_target(project, entity, node=False)
            if target is not None:
                done((entity.get("name", f"Element-{entity.get('tag')}"), target))
                return

        matches = _matches(entity, candidates, project)
        if len(matches) == 1:
            done(matches[0])
        elif not matches:
            viewport.message.emit("The picked viewport entity is not a valid target")
        else:
            viewport.message.emit("The picked viewport entity belongs to multiple targets; select one from the list")

    viewport.begin_context_pick(allowed, selected)


def _matches(entity, candidates, project=None):
    tag = str(entity.get("tag", ""))
    kind = str(entity.get("kind", "")).lower()
    if kind == "rp":
        result = []
        for item in candidates:
            value = _candidate_value(item)
            if str(getattr(value, "id", "")) == tag:
                result.append(item)
        return result

    labels = _labels(entity)
    result = []
    for candidate in candidates:
        value = _candidate_value(candidate)
        if not hasattr(value, "members"):
            continue
        if project is not None:
            from opencae.model.core import region_member_label
            members = {_normalize(region_member_label(project, member)) for member in value.members}
        else:
            members = {_normalize(member) for member in value.members}
        if members & labels:
            result.append(candidate)
    return result


def _candidate_value(candidate):
    if isinstance(candidate, tuple) and len(candidate) == 2:
        return candidate[1]
    return candidate


def _labels(entity):
    name = _normalize(entity.get("name", ""))
    instance = str(entity.get("instance") or "").strip()
    kind = str(entity.get("kind") or entity.get("mesh_entity") or "").strip().lower()
    tag = entity.get("tag")
    labels = {name} if name else set()
    if tag not in (None, ""):
        canonical = {"node": "Node", "element": "Element", "face": "Face", "edge": "Edge", "cell": "Cell", "vertex": "Vertex"}.get(kind)
        if canonical:
            local = f"{canonical}-{tag}"
            labels.add(_normalize(local))
            if instance:
                labels.add(_normalize(f"{instance}.{local}"))
    return labels


def _normalize(value):
    return str(value or "").strip().replace("/", ".").casefold()


def _mesh_target(project, entity, *, node):
    from opencae.model.core import EntityRef, MeshElementTarget, MeshNodeTarget

    instance_id = str(entity.get("instance_id") or "")
    owner = project.try_resolve(instance_id) if instance_id else None
    instance_name = str(entity.get("instance") or "")
    if owner is None:
        matches = [item for item in project.assembly.instances if item.name.casefold() == instance_name.casefold()]
        owner = matches[0] if len(matches) == 1 else None
    if owner is None and not instance_name and len(project.parts) == 1:
        owner = project.parts[0]
    if owner is None:
        return None
    tag = int(entity.get("tag", 0))
    owner_ref = EntityRef.of(owner, type(owner).__name__)
    return MeshNodeTarget(owner_ref, tag) if node else MeshElementTarget(owner_ref, tag)
