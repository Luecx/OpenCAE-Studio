from collections import defaultdict, deque

from opencae.model.element_catalog import CATALOG
from .element_records import records


def propagation_closure(mesh, selected_ids):
    elements = records(mesh); selected = {eid for eid in selected_ids if eid in elements}
    if not selected: return set()
    dimension = CATALOG[elements[next(iter(selected))].topology].dimension
    if dimension == 1: return selected
    interfaces = defaultdict(list)
    for element in elements.values():
        info = CATALOG[element.topology]
        if info.dimension != dimension: continue
        primary = element.connectivity[:info.primary_nodes]
        entities = info.edges if dimension == 2 else info.faces
        for entity in entities:
            interfaces[tuple(sorted(primary[index] for index in entity))].append(element.element_id)
    neighbors = defaultdict(set)
    for attached in interfaces.values():
        if len(attached) < 2: continue
        for current in attached: neighbors[current].update(value for value in attached if value != current)
    result = set(selected); queue = deque(selected)
    while queue:
        current = queue.popleft()
        for neighbor in neighbors[current]:
            if neighbor not in result: result.add(neighbor); queue.append(neighbor)
    return result
