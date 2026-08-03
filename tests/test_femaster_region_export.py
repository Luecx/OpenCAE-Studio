from __future__ import annotations

import re

from opencae.model.core import EntityRef
from opencae.model.entities.loads import ConcentratedLoad
from opencae.model.selection import (
    GeometryOperand,
    NodalLoadDistribution,
    RegionDefinition,
    RegionSelectionItem,
)


def test_complete_femaster_export_uses_resolved_regions(project_factory):
    data = project_factory()
    deck = data["project"].render_deck("FEMaster", data["analysis"])
    assert "*NSET" in deck
    assert "*ELSET" in deck
    assert "*SURFACE" in deck
    assert "*CLOAD" in deck
    assert "*PLOAD" in deck
    assert "*COUPLING" in deck
    assert "*TIE" in deck
    coupling_line = next(line for line in deck.splitlines() if line.startswith("*COUPLING"))
    assert "ADJUST" not in coupling_line and "DISTANCE" not in coupling_line
    tie_line = next(line for line in deck.splitlines() if line.startswith("*TIE"))
    assert "ADJUST=ON" in tie_line and "DISTANCE=0.1" in tie_line


def test_total_uniform_cload_divides_by_resolved_node_count(project_factory):
    data = project_factory(include_constraints=False)
    deck = data["project"].render_deck("FEMaster", data["analysis"])
    lines = deck.splitlines()
    index = next(i for i, line in enumerate(lines) if line.startswith("*CLOAD"))
    values = [value.strip() for value in lines[index + 1].split(",")]
    assert float(values[1]) == 50.0


def test_per_node_cload_preserves_component(project_factory):
    data = project_factory(include_constraints=False)
    part, instance = data["part"], data["instance_1"]
    load = ConcentratedLoad(
        name="PER_NODE",
        target=RegionDefinition((RegionSelectionItem(GeometryOperand(EntityRef.of(part, "Part"), 2, 1, EntityRef.of(instance, "Instance"))),)),
        components=[90.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        distribution=NodalLoadDistribution.PER_NODE,
    )
    data["project"].loads = [load]
    data["analysis"].steps[0].load_refs = [EntityRef.of(load, "Load")]
    data["project"].rebuild_index()
    deck = data["project"].render_deck("FEMaster", data["analysis"])
    lines = deck.splitlines(); index = next(i for i, line in enumerate(lines) if line.startswith("*CLOAD"))
    assert float(lines[index + 1].split(",")[1]) == 90.0


def test_part_region_occurrences_export_as_distinct_sets(project_factory):
    data = project_factory(include_constraints=False)
    deck = data["project"].render_deck("FEMaster", data["analysis"])
    set_headers = [line for line in deck.splitlines() if line.startswith("*NSET") and "VERTEX_SET" in line]
    assert len(set_headers) == 2
    assert len(set(set_headers)) == 2


def test_pressure_mesh_facet_exports_only_clicked_local_face(project_factory):
    from opencae.model.entities.loads import PressureLoad
    from opencae.model.selection import MeshFacetOperand

    data = project_factory(include_constraints=False)
    part, instance = data["part"], data["instance_1"]
    pressure = PressureLoad(
        name="FACET_PRESSURE",
        target=RegionDefinition((RegionSelectionItem(MeshFacetOperand(
            EntityRef.of(part, "Part"), 1, "S2", EntityRef.of(instance, "Instance"), part.mesh.revision,
        )),)),
        pressure=3.0,
    )
    data["project"].loads = [pressure]
    data["analysis"].steps[0].load_refs = [EntityRef.of(pressure, "Load")]
    data["project"].rebuild_index()
    deck = data["project"].render_deck("FEMaster", data["analysis"])
    lines = deck.splitlines()
    header = next(i for i, line in enumerate(lines) if line.startswith("*SURFACE") and "FACET_PRESSURE_TARGET" in line)
    assert lines[header + 1].endswith(", S2")
    assert not any(line.endswith(", S1") for line in lines[header + 1:header + 2])


def test_part_reference_point_occurrences_always_export_distinct_nsets(project_factory):
    data = project_factory()
    deck = data["project"].render_deck("FEMaster", data["analysis"])
    headers = [line for line in deck.splitlines() if line.startswith("*NSET") and "RP_PART_RP" in line]
    assert len(headers) == 2
    assert len(set(headers)) == 2


def test_geometry_vertex_is_valid_coupling_control_node(project_factory):
    data = project_factory()
    deck = data["project"].render_deck("FEMaster", data["analysis"])
    lines = deck.splitlines()
    header = next(i for i, line in enumerate(lines) if line.startswith("*NSET") and "COUPLING_CONTROL" in line)
    assert lines[header + 1].strip() == "1"
    coupling = next(line for line in lines if line.startswith("*COUPLING"))
    assert "MASTER=COUPLING_CONTROL" in coupling


def test_section_assignment_is_materialized_per_instance_occurrence(project_factory):
    data = project_factory()
    deck = data["project"].render_deck("FEMaster", data["analysis"])
    headers = [line for line in deck.splitlines() if line.startswith("*ELSET") and "SECTION_ASSIGNMENT" in line]
    assert len(headers) == 2
    assert any("I1_SECTION_ASSIGNMENT" in line for line in headers)
    assert any("I2_SECTION_ASSIGNMENT" in line for line in headers)


def test_mesh_node_is_valid_coupling_control_node(project_factory):
    from opencae.model.entities.constraints import KinematicCoupling
    from opencae.model.selection import MeshNodeOperand

    data = project_factory(include_constraints=False)
    part, instance = data["part"], data["instance_1"]
    coupling = KinematicCoupling(
        name="NODE_COUPLING",
        control_point=RegionDefinition((RegionSelectionItem(MeshNodeOperand(
            EntityRef.of(part, "Part"), 2, EntityRef.of(instance, "Instance"), part.mesh.revision,
        )),)),
        slave=RegionDefinition((RegionSelectionItem(GeometryOperand(
            EntityRef.of(part, "Part"), 2, 1, EntityRef.of(instance, "Instance"),
        )),)),
    )
    data["project"].assembly.constraints = [coupling]
    data["project"].rebuild_index()
    deck = data["project"].render_deck("FEMaster", data["analysis"])
    lines = deck.splitlines()
    header = next(i for i, line in enumerate(lines) if line.startswith("*NSET") and "NODE_COUPLING_CONTROL" in line)
    assert lines[header + 1].strip() == "2"
