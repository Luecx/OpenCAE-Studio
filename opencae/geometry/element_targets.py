import re

from opencae.model.element_catalog import CATALOG
from opencae.model.core import EntityRef, RegionMemberKind, RegionMemberRef
from .element_records import records

_ELEMENT = re.compile(r"(?:^|\.)Element-(\d+)$", re.I)


def resolve_target_ids(part, targets):
    elements = records(part.mesh)
    available = set(elements)
    if not targets:
        return available
    result = set()
    for target in targets:
        _resolve(part, elements, target, result, set())
    return result & available


def _resolve(part, elements, target, result, visited):
    key = _target_key(target)
    if key in visited:
        return
    visited.add(key)

    if isinstance(target, EntityRef):
        region = next((item for item in part.element_sets if item.id == target.entity_id), None)
        if region:
            for member in region.members:
                _resolve(part, elements, member, result, visited)
        return

    text = _local_label(target)
    match = _ELEMENT.search(text)
    if match:
        result.add(int(match.group(1)))
        return
    label = text.split(".")[-1]
    direct = set(map(int, part.mesh.entity_elements.get(label, ()))) & set(elements)
    if direct:
        result.update(direct)
        return
    if label in part.mesh.entity_nodes:
        result.update(_from_entity_nodes(elements, set(map(int, part.mesh.entity_nodes[label])), label))
        return
    name = text.split(":", 1)[1] if text.casefold().startswith("elementset:") else text
    region = next((item for item in part.element_sets if item.name.casefold() == name.casefold()), None)
    if region:
        for member in region.members:
            _resolve(part, elements, member, result, visited)


def _target_key(target):
    if isinstance(target, EntityRef):
        return ("set", target.entity_id or target.legacy_name.casefold())
    if isinstance(target, RegionMemberRef):
        return ("member", target.kind.value, target.owner_ref.entity_id, target.tag, target.legacy_label)
    return ("legacy", str(target).casefold())


def _from_entity_nodes(elements, nodes, label):
    kind = label.split("-", 1)[0].lower()
    result = set()
    for element in elements.values():
        info = CATALOG[element.topology]
        primary = element.connectivity[:info.primary_nodes]
        entities = (
            info.faces if kind == "face" and info.dimension == 3
            else info.edges if kind == "edge" and info.dimension >= 2
            else (tuple(range(info.primary_nodes)),)
        )
        if any(set(primary[index] for index in entity) <= nodes for entity in entities):
            result.add(element.element_id)
    return result


def _local_label(member):
    if isinstance(member, RegionMemberRef):
        if member.kind in {RegionMemberKind.REFERENCE_POINT, RegionMemberKind.UNKNOWN}:
            return member.legacy_label
        return f"{member.kind.value}-{member.tag}"
    return str(member)
