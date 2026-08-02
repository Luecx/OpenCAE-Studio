from dataclasses import dataclass
from collections import Counter

from opencae.model.element_catalog import CATALOG
from opencae.model.entities.mesh import ElementOrder
from .element_adjacency import propagation_closure
from .element_records import records
from .element_targets import resolve_target_ids


@dataclass(frozen=True)
class TopologySummary:
    key: object
    label: str
    count: int
    first: int
    second: int
    formulations: dict[str, int]


@dataclass(frozen=True)
class ConversionPreview:
    selected: frozenset[int]
    affected: frozenset[int]
    additional_by_topology: dict[str, int]

    @property
    def additional(self): return len(self.affected - self.selected)


def summarize(part, targets):
    elements = records(part.mesh); target = resolve_target_ids(part, targets); grouped = {}
    for element_id in target:
        element = elements[element_id]; grouped.setdefault(element.topology, []).append(element)
    return [TopologySummary(key, CATALOG[key].label, len(values),
                            sum(value.order == ElementOrder.FIRST for value in values),
                            sum(value.order == ElementOrder.SECOND for value in values),
                            dict(Counter(value.formulation for value in values)))
            for key, values in sorted(grouped.items(), key=lambda item: CATALOG[item[0]].label)]


def preview(part, targets, topology):
    elements = records(part.mesh); target = resolve_target_ids(part, targets)
    selected = {eid for eid in target if elements[eid].topology == topology}
    affected = propagation_closure(part.mesh, selected); counter = Counter()
    for eid in affected - selected: counter[CATALOG[elements[eid].topology].label] += 1
    return ConversionPreview(frozenset(selected), frozenset(affected), dict(counter))
