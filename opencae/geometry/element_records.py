from dataclasses import dataclass

from opencae.model.element_catalog import CATALOG, topology_key
from opencae.model.entities.mesh import ElementOrder


@dataclass
class MeshElement:
    element_id: int
    topology: object
    order: ElementOrder
    formulation: str
    connectivity: tuple[int, ...]


def records(mesh):
    values = {}
    for block in mesh.element_blocks:
        key = topology_key(block.definition)
        if key is None: continue
        info = CATALOG[key]; order = ElementOrder.SECOND if block.definition.order == "Quadratic" else ElementOrder.FIRST
        formulation = _formulation(block.definition)
        for element_id, connectivity in zip(block.ids, block.connectivity):
            values[int(element_id)] = MeshElement(int(element_id), key, order, formulation, tuple(map(int, connectivity)))
    return values


def _formulation(definition):
    if definition.topology == "Beam Elements": return "Beam"
    if definition.topology in {"Truss Elements", "Lines"}: return "Truss"
    return definition.formulation or "Standard"
