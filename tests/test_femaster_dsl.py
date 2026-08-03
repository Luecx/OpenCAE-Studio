import unittest

from opencae.model.core import EntityRef, NodeSetTarget
from opencae.model.entities.analysis.analysis import Analysis
from opencae.model.entities.analysis.step import AnalysisStep
from opencae.model.entities.assembly.instance import Instance
from opencae.model.entities.elements.tetrahedron import TetrahedronElementDefinition
from opencae.model.entities.loads.force import ForceLoad
from opencae.model.entities.mesh.element_block import ElementBlock
from opencae.model.entities.mesh.node_table import NodeTable
from opencae.model.entities.parts.part import Part
from opencae.model.entities.project import Project
from opencae.model.entities.regions.region import Region
from opencae.model.entities.regions.section_assignment import SectionAssignment
from opencae.model.entities.resources.material import Material
from opencae.model.entities.resources.material_behaviors import IsotropicElasticity
from opencae.model.entities.sections.solid import SolidSection
from opencae.model.entities.supports.fixed import FixedSupport
from opencae.solvers.femaster import FEMasterAdapter
from opencae.solvers.femaster_dsl.validator import validate_deck


class FEMasterDslTest(unittest.TestCase):
    def test_geometry_backed_sets_and_surface(self):
        project = _project()
        deck = FEMasterAdapter().write_deck_text(project, project.analyses[0])
        self.assertFalse(validate_deck(deck))
        self.assertIn("*NSET, NSET=P_1_FACE_NODES\n1\n2\n3", deck)
        self.assertIn("*ELSET, ELSET=P_1_CELL_ELEMENTS\n1", deck)
        self.assertIn("*SURFACE, NAME=P_1_PRESSURE\n1, 1, S1", deck)
        self.assertIn("*LOADCASE, TYPE=LINEARSTATIC, NAME=STEP", deck)
        self.assertNotIn("1, 2, 3", deck.split("*NSET, NSET=P_1_FACE_NODES", 1)[1].split("*", 1)[0])

    def test_assembly_regions_are_resolved(self):
        project = _project()
        project.assembly.node_sets.append(Region(name="ASM_NODES", region_type="Node Set", scope="Assembly", members=["P.Face-1"]))
        project.assembly.element_sets.append(Region(name="ASM_ELEMENTS", region_type="Element Set", scope="Assembly", members=["P.Cell-1"]))
        project.assembly.surfaces.append(Region(name="ASM_SURFACE", region_type="Surface", scope="Assembly", members=["P.Face-1"]))
        deck = FEMasterAdapter().write_deck_text(project, project.analyses[0])
        self.assertIn("*NSET, NSET=ASM_NODES\n1\n2\n3", deck)
        self.assertIn("*ELSET, ELSET=ASM_ELEMENTS\n1", deck)
        self.assertIn("*SURFACE, NAME=ASM_SURFACE\n3, 1, S1", deck)


def _project():
    project = Project(name="TEST")
    material = Material(
        name="STEEL",
        behaviors=[IsotropicElasticity(youngs_modulus=210000.0, poisson_ratio=0.3)],
    )
    section = SolidSection(name="SOLID", material_ref=EntityRef.of(material))
    project.materials.append(material)
    project.sections.append(section)

    part = Part(name="P")
    part.mesh.nodes = NodeTable(
        ids=[1, 2, 3, 4],
        coordinates=[(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)],
    )
    part.mesh.element_blocks = [ElementBlock(
        definition=TetrahedronElementDefinition(name="Tetrahedra"),
        ids=[1], connectivity=[(1, 2, 3, 4)],
    )]
    part.mesh.entity_nodes = {"Face-1": [1, 2, 3], "Cell-1": [1, 2, 3, 4]}
    part.mesh.entity_elements = {"Cell-1": [1]}
    part_node_set = Region(name="FACE_NODES", region_type="Node Set", members=["Face-1"])
    part_element_set = Region(name="CELL_ELEMENTS", region_type="Element Set", members=["Cell-1"])
    part_surface = Region(name="PRESSURE", region_type="Surface", members=["Face-1"])
    part.node_sets = [part_node_set]
    part.element_sets = [part_element_set]
    part.surfaces = [part_surface]
    part.section_assignments = [SectionAssignment(
        name="Section Assignment", section_ref=EntityRef.of(section), region_ref=EntityRef.of(part_element_set),
    )]
    project.parts.append(part)

    instance = Instance(name="P-1", part_ref=EntityRef.of(part))
    project.assembly.instances.append(instance)
    assembly_node_set = Region(name="FACE_NODES", region_type="Node Set", scope="Assembly", members=["P-1.Face-1"])
    assembly_element_set = Region(name="CELL_ELEMENTS", region_type="Element Set", scope="Assembly", members=["P-1.Cell-1"])
    assembly_surface = Region(name="PRESSURE", region_type="Surface", scope="Assembly", members=["P-1.Face-1"])
    project.assembly.node_sets.append(assembly_node_set)
    project.assembly.element_sets.append(assembly_element_set)
    project.assembly.surfaces.append(assembly_surface)

    support = FixedSupport(name="BC", target=NodeSetTarget(ref=EntityRef.of(assembly_node_set)))
    load = ForceLoad(name="FORCE", target=NodeSetTarget(ref=EntityRef.of(assembly_node_set)), magnitude=1.0)
    project.supports.append(support)
    project.loads.append(load)
    project.analyses.append(Analysis(
        name="STATIC", analysis_type="Linear Static",
        steps=[AnalysisStep(
            name="STEP", step_type="Linear Static",
            load_refs=[EntityRef.of(load)], support_refs=[EntityRef.of(support)],
        )],
    ))
    project.rebuild_index(strict=True)
    return project


if __name__ == "__main__":
    unittest.main()
