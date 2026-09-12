"""End-to-end regressions for editable mesh ownership, validation, and UI state."""

from copy import deepcopy

from opencae.model.entities.fem import MeshEntityOrigin, Node, Tet4
from opencae.model.entities.mesh import (
    ElementBlock,
    GeometryEntityRef,
    MeshState,
    NodeTable,
    RemeshPolicy,
    RemeshReplacementMode,
    merge_remesh_result,
    suggested_orientation_repair,
    validate_element,
)
from opencae.model.selection import RegionProjection, RegionRequirement, RegionResolver
from opencae.persistence.project_codec import project_from_dict, project_to_dict
from opencae.ui.dialogs.mesh_bulk import MeshElementBulkDialog, MeshNodeBulkDialog
from opencae.ui.dialogs.mesh_element import MeshElementDialog
from opencae.ui.dialogs.mesh_node import MeshNodeDialog


def _dispose_widgets(application, *widgets):
    """Destroy Qt test widgets deterministically before later VTK-bearing tests."""
    for widget in widgets:
        widget.close()
        widget.deleteLater()
    application.processEvents()


def test_schema_23_mesh_migrates_to_split_mesh_and_typed_associations(project_factory):
    project = project_factory(include_constraints=False)["project"]
    encoded = project_to_dict(project); encoded["schema_version"] = 23
    persisted_part = encoded["project"]["parts"][0]
    current = persisted_part["mesh"]; finite = current["finite_elements"]
    nodes = deepcopy(finite["nodes"]); nodes.pop("origins", None)
    blocks = deepcopy(finite["element_blocks"])
    for block in blocks: block.pop("origins", None)
    persisted_part["mesh"] = {
        "__type__": "mesh_state", "settings": current["recipe"]["settings"],
        "seeds": current["recipe"]["seeds"], "element_controls": current["recipe"]["element_controls"],
        "nodes": nodes, "element_definitions": finite["element_definitions"], "element_blocks": blocks,
        "entity_nodes": {"Vertex-1": [1], "Face-1": [1, 2, 3]},
        "entity_elements": {"Face-1": [1], "Cell-1": [1]}, "entity_facets": {"Face-1": [(1, "S1")]},
        "node_count": 4, "element_count": 1, "mesh_dimension": 3,
        "minimum_quality": None, "mean_quality": None, "status": "Current", "revision": "mesh-r1",
    }
    persisted_part["regions"][0]["definition"] = ["Vertex-1"]
    restored = project_from_dict(encoded); mesh = restored.parts[0].mesh
    typed = dict(mesh.associations.nodes.typed_items())
    assert GeometryEntityRef(0, 1) in typed
    assert GeometryEntityRef(2, 1) in typed
    assert mesh.nodes.origins == [MeshEntityOrigin.GENERATED] * 4
    assert mesh.element_blocks[0].origins == [MeshEntityOrigin.GENERATED]
    assert restored.parts[0].regions[0].definition.items[0].operand.legacy_label == "Vertex-1"


def test_region_resolver_reads_typed_geometry_associations(project_factory):
    values = project_factory(include_constraints=False); project = values["project"]; part = values["part"]
    result = RegionResolver(project).resolve(values["face_region"].definition, RegionRequirement(RegionProjection.FACETS, (2,), 1), allow_part_local=True)
    assert result.valid
    assert {(item.element_id, item.local_face) for item in result.facets} == {(1, "S1")}
    assert isinstance(part.mesh.associations.facets.typed_items()[0][0], GeometryEntityRef)


def test_manual_node_move_invalidates_only_incident_mesh_and_detaches_cad(project_factory):
    part = project_factory(include_constraints=False)["part"]
    assert part.mesh.entity_nodes["Vertex-1"] == [1]
    part.mesh.move_node(1, (0.0, 0.0, 1.0))
    assert 1 in part.mesh.quality.invalid_element_ids
    assert part.mesh.lifecycle.validity.value == "Invalid"
    assert part.mesh.entity_nodes.get("Vertex-1", []) == []
    assert part.mesh.lifecycle.geometry_association.value == "Detached"


def test_inverted_tet_has_explicit_orientation_repair():
    nodes = (Node(1, (1.0, 0.0, 0.0)), Node(2, (0.0, 0.0, 0.0)), Node(3, (0.0, 1.0, 0.0)), Node(4, (0.0, 0.0, 1.0)))
    element = Tet4(7, nodes); result = validate_element(element); repair = suggested_orientation_repair(element)
    assert result.inverted; assert repair == (2, 1, 3, 4)
    repaired_nodes = {node.id: node for node in nodes}; repaired = Tet4(7, tuple(repaired_nodes[value] for value in repair))
    assert validate_element(repaired).valid


def test_replace_generated_remesh_preserves_authored_ids_and_remaps_collisions(project_factory):
    part = project_factory(include_constraints=False)["part"]; existing = part.mesh
    existing.element_blocks[0].origins = [MeshEntityOrigin.AUTHORED]
    definition = deepcopy(existing.element_definitions[0])
    generated = MeshState(
        nodes=NodeTable(ids=[1, 2, 3, 4], coordinates=[(0.0,0.0,0.0),(2.0,0.0,0.0),(0.0,2.0,0.0),(0.0,0.0,2.0)], origins=[MeshEntityOrigin.GENERATED]*4),
        element_blocks=[ElementBlock(definition, [1], [(1,2,3,4)], [MeshEntityOrigin.GENERATED])],
        entity_nodes={"Cell-1":[1,2,3,4]}, entity_elements={"Cell-1":[1]}, status="Current", revision="new-r1",
    )
    merge_remesh_result(existing, generated, RemeshPolicy(replacement=RemeshReplacementMode.REPLACE_GENERATED))
    assert {element.id for element in generated.iter_elements()} == {1, 2}
    assert generated.element(1).origin is MeshEntityOrigin.AUTHORED
    assert generated.element(1).connectivity == (1,2,3,4)
    assert generated.element(2).origin is MeshEntityOrigin.GENERATED
    assert min(generated.element(2).connectivity) > 4
    assert {1,2,3,4}.issubset(set(generated.nodes.ids))


def test_element_dialog_preserves_pick_order_and_removal(qapplication):
    dialog = MeshElementDialog(selected_node_ids=(3,1), available_node_ids=(1,2,3,4))
    try:
        dialog.apply_picked_node(4); dialog.apply_picked_node(1, remove=True)
        assert dialog.node_ids() == (3,4)
        dialog.set_node_ids((4,3,2,1)); assert dialog.values()["node_ids"] == (4,3,2,1)
    finally:
        _dispose_widgets(qapplication, dialog)


def test_node_and_bulk_dialogs_return_editable_values(qapplication):
    node = Node(5, (1.0,2.0,3.0), MeshEntityOrigin.AUTHORED)
    single = MeshNodeDialog(node); bulk = MeshNodeBulkDialog((node,))
    try:
        single.set_coordinates((4.0,5.0,6.0))
        assert single.values()["coordinates"] == (4.0,5.0,6.0)
        bulk.translation.set_value((1.0,-1.0,2.0))
        assert bulk.values()[5] == (2.0,1.0,5.0)
    finally:
        _dispose_widgets(qapplication, single, bulk)


def test_element_bulk_dialog_can_apply_common_compatible_type(qapplication):
    nodes = (Node(1,(0.0,0.0,0.0)), Node(2,(1.0,0.0,0.0)), Node(3,(0.0,1.0,0.0)), Node(4,(0.0,0.0,1.0)))
    element = Tet4(1, nodes); dialog = MeshElementBulkDialog((element,), available_node_ids=(1,2,3,4))
    try:
        values = dialog.values()
        assert values[0]["element_type"] is Tet4; assert values[0]["node_ids"] == (1,2,3,4)
    finally:
        _dispose_widgets(qapplication, dialog)
