from opencae.model.element_catalog import resulting_type, topology_key
from opencae.model.entities.mesh import ElementOrder, ElementTopology

ELEMENT_TYPES = {
    "C3D4", "C3D5", "C3D6", "C3D8", "C3D8R", "C3D10", "C3D13", "C3D15", "C3D20", "C3D20R",
    "S3", "MITC3FRT", "S4", "MITC4", "MITC4FRT", "S6", "MITC6FRT", "S8", "MITC8", "MITC8FRT", "QSPT",
    "B33", "T3",
}


def element_type(definition, node_count=None):
    key = topology_key(definition)
    if key is None: return None
    limits = {ElementTopology.LINE:2, ElementTopology.SHELL_TRI:3, ElementTopology.SHELL_QUAD:4, ElementTopology.SOLID_TET:4, ElementTopology.SOLID_PYRAMID:5, ElementTopology.SOLID_WEDGE:6, ElementTopology.SOLID_HEX:8}
    second = definition.order == "Quadratic" or (node_count or 0) > limits[key]
    order = ElementOrder.SECOND if second else ElementOrder.FIRST
    if key == ElementTopology.LINE and second:
        raise ValueError("FEMaster does not support quadratic beam or truss line elements")
    formulation = definition.formulation or "Standard"
    if definition.topology == "Beam Elements": formulation = "Beam"
    elif definition.topology in {"Truss Elements", "Lines"}: formulation = "Truss"
    return resulting_type(key, order, formulation)
