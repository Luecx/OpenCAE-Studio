from __future__ import annotations

import re

from opencae.model.element_catalog import CATALOG
from opencae.model.selection import RegionDefinition, local_element_ids
from .element_records import records

_ELEMENT = re.compile(r"(?:^|\.)Element-(\d+)$", re.I)


def resolve_target_ids(part, target, project=None):
    """Resolve element-control targets.

    RegionDefinition is the canonical representation. A small legacy adapter is
    retained for loading pre-schema-15 element controls; it is not used by new
    dialogs or controllers.
    """
    if isinstance(target, RegionDefinition):
        if project is not None:
            from opencae.model.selection import RegionProjection, RegionRequirement, RegionResolver
            resolved = RegionResolver(project).resolve(
                target, RegionRequirement(RegionProjection.ELEMENTS, (0, 1, 2, 3), 0),
            )
            return {item.element_id for item in resolved.elements if item.owner_id == part.id}
        return local_element_ids(part, target)
    return _legacy_target_ids(part, target)


def elements_from_geometry_label(part, label: str) -> set[int]:
    elements = records(part.mesh)
    available = set(elements)
    direct = set(map(int, part.mesh.entity_elements.get(label, ()))) & available
    if direct:
        return direct
    nodes = set(map(int, part.mesh.entity_nodes.get(label, ())))
    return _from_entity_nodes(elements, nodes, label) if nodes else set()


def _legacy_target_ids(part, targets):
    elements = records(part.mesh)
    available = set(elements)
    if not targets:
        return available
    result = set()
    for target in targets:
        text = str(target)
        match = _ELEMENT.search(text)
        if match:
            result.add(int(match.group(1)))
            continue
        label = text.split(".")[-1]
        result.update(elements_from_geometry_label(part, label))
        name = text.split(":", 1)[1] if text.casefold().startswith("elementset:") else text
        region = next((item for item in part.regions if item.name.casefold() == name.casefold()), None)
        if region:
            result.update(local_element_ids(part, region.definition))
    return result & available


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
