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


def _matches(entity, candidates, project=None):
    tag = str(entity.get("tag", ""))
    kind = str(entity.get("kind", "")).lower()
    if kind == "rp":
        return [item for item in candidates if str(getattr(item, "id", "")) == tag]

    labels = _labels(entity)
    result = []
    for candidate in candidates:
        if project is not None:
            from opencae.model.core import region_member_label
            members = {_normalize(region_member_label(project, value)) for value in getattr(candidate, "members", ())}
        else:
            members = {_normalize(value) for value in getattr(candidate, "members", ())}
        if members & labels:
            result.append(candidate)
    return result


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


def begin_target_pick(project, viewport, candidates, allowed, done, *, mesh_nodes=False, mesh_elements=False) -> None:
    """Pick either an existing region/reference point or a direct mesh member."""
    candidates = tuple(candidates)

    def selected(entity):
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
