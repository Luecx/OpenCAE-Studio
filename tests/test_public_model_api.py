from __future__ import annotations

import pytest

from opencae.api import Hex8, Model, Tet4


def test_public_relationships_are_python_objects_not_strings():
    model = Model.create("api")
    part = model.part("Bracket")
    material = model.material(
        "Steel",
        youngs_modulus=210000.0,
        poisson_ratio=0.3,
    )
    section = model.section("Solid", material=material)
    instance = model.instance(part)

    assert section.material is material
    assert instance.part is part
    assert section.material_ref.entity_id == material.id
    assert instance.part_ref.entity_id == part.id
    assert not hasattr(section.material_ref, "legacy_name")
    assert not hasattr(instance.part_ref, "legacy_name")

    with pytest.raises(TypeError):
        instance.part = part.name


def test_nodes_and_elements_have_clean_object_connectivity():
    model = Model.create("mesh")
    part = model.part("Part")
    nodes = (
        model.node(part, (0, 0, 0)),
        model.node(part, (1, 0, 0)),
        model.node(part, (0, 1, 0)),
        model.node(part, (0, 0, 1)),
    )
    element = model.element(part, Tet4, nodes)

    assert element.nodes == nodes
    assert element.connectivity == tuple(node.id for node in nodes)
    assert tuple(part.mesh.iter_elements()) == (element,)


def test_element_topology_is_validated_at_construction():
    model = Model.create("mesh")
    part = model.part("Part")
    nodes = [model.node(part, (index, 0, 0)) for index in range(4)]

    with pytest.raises(ValueError):
        model.element(part, Hex8, nodes)


def test_named_regions_are_passed_to_load_api_as_objects():
    model = Model.create("load")
    part = model.part("Part")
    nodes = (
        model.node(part, (0, 0, 0)),
        model.node(part, (1, 0, 0)),
    )
    node_set = model.node_set(part, "LoadedNodes", nodes)
    instance = model.instance(part)
    load = model.concentrated_load(
        "Force",
        target=node_set,
        components=(1, 0, 0, 0, 0, 0),
        instance=instance,
    )

    operand = load.target.operands[0]
    assert operand.region_ref.entity_id == node_set.id
    assert not hasattr(operand.region_ref, "legacy_name")
    model.validate()
