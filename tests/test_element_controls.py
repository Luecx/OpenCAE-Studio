from pathlib import Path
from tempfile import TemporaryDirectory

from opencae.geometry.element_adjacency import propagation_closure
from opencae.geometry.element_control_summary import preview, summarize
from opencae.geometry.element_controls_apply import apply_control
from opencae.model.entities.elements import QuadrilateralShellElementDefinition, TetrahedronElementDefinition, TriangleShellElementDefinition
from opencae.model.entities.mesh import ElementBlock, ElementControl, ElementOrder, ElementTopology, NodeTable
from opencae.model.entities.parts.part import Part
from opencae.model.entities.project import Project
from opencae.persistence.project_io import load_project, save_project


def _part():
    part = Part(name="P"); part.mesh.nodes = NodeTable(
        ids=list(range(1, 15)), coordinates=[(float(i), float(i % 3), float(i % 5)) for i in range(1, 15)],
    ); return part


def test_mixed_order_is_reported_for_one_topology():
    part = _part(); part.mesh.element_blocks = [
        ElementBlock(TetrahedronElementDefinition(name="C3D4", order="Linear"), [1], [(1, 2, 3, 4)]),
        ElementBlock(TetrahedronElementDefinition(name="C3D10", order="Quadratic"), [2], [(5, 6, 7, 8, 9, 10, 11, 12, 13, 14)]),
    ]
    value = summarize(part, [])[0]
    assert value.first == 1 and value.second == 1 and value.count == 2


def test_order_propagates_across_shared_shell_edge_but_not_line_endpoint():
    part = _part(); part.mesh.element_blocks = [
        ElementBlock(TriangleShellElementDefinition(name="S3"), [1], [(1, 2, 3)]),
        ElementBlock(QuadrilateralShellElementDefinition(name="S4"), [2], [(2, 1, 4, 5)]),
    ]
    assert propagation_closure(part.mesh, {1}) == {1, 2}
    from opencae.model.entities.elements.line import LineElementDefinition
    part.mesh.element_blocks = [ElementBlock(LineElementDefinition(name="L"), [3, 4], [(1, 2), (2, 3)])]
    assert propagation_closure(part.mesh, {3}) == {3}


def test_second_order_conversion_shares_midside_nodes():
    part = _part(); part.mesh.element_blocks = [ElementBlock(
        TetrahedronElementDefinition(name="C3D4"), [1, 2], [(1, 2, 3, 4), (1, 3, 2, 5)],
    )]
    control = ElementControl(name="EC", targets=["Element-1"], topology=ElementTopology.SOLID_TET, order=ElementOrder.SECOND)
    selected, affected = apply_control(part, control)
    assert selected == {1} and affected == {1, 2}
    rows = {eid: row for block in part.mesh.element_blocks for eid, row in zip(block.ids, block.connectivity)}
    assert len(rows[1]) == len(rows[2]) == 10
    assert set(rows[1][4:7]) == set(rows[2][4:7])


def test_preview_reports_elements_outside_target():
    part = _part(); part.mesh.element_blocks = [ElementBlock(
        TetrahedronElementDefinition(name="C3D4"), [1, 2], [(1, 2, 3, 4), (1, 3, 2, 5)],
    )]
    value = preview(part, ["Element-1"], ElementTopology.SOLID_TET)
    assert value.selected == {1}; assert value.affected == {1, 2}; assert value.additional == 1


def test_element_control_survives_project_roundtrip():
    project = Project(name="P"); part = _part(); project.parts.append(part)
    part.mesh.element_controls.append(ElementControl(name="EC", targets=["Cell-1"], topology=ElementTopology.SOLID_HEX,
                                                       order=ElementOrder.SECOND, formulation="Reduced Integration"))
    with TemporaryDirectory() as directory:
        path = Path(directory) / "model.ocae"; save_project(project, path); loaded = load_project(path)
    value = loaded.parts[0].mesh.element_controls[0]
    assert value.topology == ElementTopology.SOLID_HEX; assert value.order == ElementOrder.SECOND


def test_solid_order_propagates_across_tet_wedge_interface():
    from opencae.model.entities.elements import PentahedronElementDefinition
    part = _part(); part.mesh.element_blocks = [
        ElementBlock(TetrahedronElementDefinition(name="C3D4"), [1], [(1, 2, 3, 4)]),
        ElementBlock(PentahedronElementDefinition(name="C3D6"), [2], [(1, 2, 3, 5, 6, 7)]),
    ]
    assert propagation_closure(part.mesh, {1}) == {1, 2}


def test_second_order_updates_geometry_entity_nodes():
    part = _part(); part.mesh.element_blocks = [ElementBlock(
        TetrahedronElementDefinition(name="C3D4"), [1], [(1, 2, 3, 4)],
    )]; part.mesh.entity_nodes = {"Face-1": [1, 2, 3]}
    apply_control(part, ElementControl(name="EC", topology=ElementTopology.SOLID_TET, order=ElementOrder.SECOND))
    assert len(part.mesh.entity_nodes["Face-1"]) == 6


def test_first_order_preserves_explicit_nodeset_members():
    from opencae.model.entities.regions.node_set import NodeSet
    part = _part(); part.mesh.element_blocks = [ElementBlock(
        TetrahedronElementDefinition(name="C3D10", order="Quadratic"), [1], [(1, 2, 3, 4, 5, 6, 7, 8, 9, 10)],
    )]; part.node_sets = [NodeSet(name="KEEP", members=["Node-5"])]
    apply_control(part, ElementControl(name="EC", topology=ElementTopology.SOLID_TET, order=ElementOrder.FIRST))
    assert 5 in part.mesh.nodes.ids
