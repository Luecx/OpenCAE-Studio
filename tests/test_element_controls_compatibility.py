from pathlib import Path
from tempfile import TemporaryDirectory

from opencae.model.core import EntityRef
from opencae.model.entities.elements import TetrahedronElementDefinition
from opencae.model.entities.mesh import ElementBlock
from opencae.model.entities.parts.part import Part
from opencae.model.entities.project import Project
from opencae.model.entities.mesh import NodeTable


def _part():
    part = Part(name="P")
    part.mesh.nodes = NodeTable(ids=list(range(1, 15)), coordinates=[(float(i), float(i % 3), float(i % 5)) for i in range(1, 15)])
    return part


def test_incompatible_beam_truss_section_is_rejected_before_export():
    from opencae.model.entities.assembly.instance import Instance
    from opencae.model.entities.elements.beam import BeamElementDefinition
    from opencae.model.entities.regions.region import Region
    from opencae.model.entities.regions.section_assignment import SectionAssignment
    from opencae.model.entities.sections.truss import TrussSection
    from opencae.model.selection import (
        MeshElementOperand,
        RegionDefinition,
        RegionProjection,
        RegionSelectionItem,
        named_region_definition,
    )
    from opencae.model.validation import validate_section_assignments

    project = Project(name="P")
    part = _part()
    project.parts.append(part)
    section = TrussSection(name="TRUSS")
    project.sections.append(section)
    part.mesh.element_blocks = [ElementBlock(BeamElementDefinition(name="B33"), [1], [(1, 2)])]
    frame = Region(
        name="FRAME",
        definition=RegionDefinition((
            RegionSelectionItem(
                MeshElementOperand(
                    EntityRef.of(part, "Part"),
                    1,
                    mesh_revision=part.mesh.revision,
                )
            ),
        )),
        preferred_projection=RegionProjection.ELEMENTS,
    )
    part.regions = [frame]
    part.section_assignments = [
        SectionAssignment(
            name="A",
            section_ref=EntityRef.of(section),
            target=named_region_definition(frame),
        )
    ]
    project.assembly.instances.append(Instance(name="P-1", part_ref=EntityRef.of(part)))
    project.rebuild_index(strict=True)

    import pytest
    with pytest.raises(ValueError, match="Truss section cannot be assigned to Beam"):
        validate_section_assignments(project)


def test_imported_line_formulations_remain_beam_and_truss():
    from opencae.geometry.element_summary import definitions_from_snapshot
    from opencae.geometry.mesh_import import read_mesh
    content = """*NODE
1,0,0,0
2,1,0,0
3,2,0,0
*ELEMENT, TYPE=B33
1,1,2
*ELEMENT, TYPE=T3
2,2,3
"""
    with TemporaryDirectory() as directory:
        path = Path(directory) / "lines.inp"; path.write_text(content); values = definitions_from_snapshot(read_mesh(path, "P"))
    assert {(item.topology, item.formulation) for item in values} == {("Beam Elements", "Beam"), ("Truss Elements", "Truss")}


def test_quadratic_line_is_rejected_for_femaster_instead_of_misexported():
    from opencae.model.entities.elements.beam import BeamElementDefinition
    from opencae.solvers.femaster_dsl.element_types import element_type
    import pytest
    with pytest.raises(ValueError, match="does not support quadratic"):
        element_type(BeamElementDefinition(name="LINE3", order="Quadratic"), 3)


def test_face_target_resolves_adjacent_solid_elements_from_entity_nodes():
    from opencae.geometry.element_targets import resolve_target_ids
    part = _part(); part.mesh.element_blocks = [ElementBlock(
        TetrahedronElementDefinition(name="C3D4"), [1, 2], [(1, 2, 3, 4), (1, 3, 2, 5)],
    )]
    part.mesh.entity_nodes = {"Face-1": [1, 2, 3]}; part.mesh.entity_elements = {"Face-1": [99]}
    assert resolve_target_ids(part, ["Face-1"]) == {1, 2}
