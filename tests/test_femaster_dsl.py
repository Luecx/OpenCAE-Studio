"""Functional regression coverage for FEMaster deck generation."""

import unittest

from opencae.model.core import EntityRef
from opencae.model.entities.amplitudes import Amplitude
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
from opencae.model.selection import (
    RegionProjection,
    RegionScope,
    definition_from_local_labels,
    named_region_definition,
)
from opencae.solvers.femaster import FEMasterAdapter
from opencae.solvers.femaster_dsl.validator import validate_deck


class FEMasterDslTest(unittest.TestCase):
    """Verify current RegionDefinition-based projects still emit valid flat decks."""

    def test_geometry_backed_sets_and_surface(self):
        """Part/assembly geometry selections materialize into flat solver regions."""
        project = _project()
        deck = FEMasterAdapter().write_deck_text(project, project.analyses[0])
        self.assertFalse(validate_deck(deck))
        self.assertIn("*NSET, NSET=P_1_FACE_NODES\n1\n2\n3", deck)
        self.assertIn("*ELSET, ELSET=P_1_CELL_ELEMENTS\n1", deck)
        self.assertIn("*SURFACE, NAME=P_1_PRESSURE\n1, 1, S1", deck)
        self.assertIn("*LOADCASE, TYPE=LINEARSTATIC, NAME=STEP", deck)
        block = deck.split("*NSET, NSET=P_1_FACE_NODES", 1)[1].split("*", 1)[0]
        self.assertNotIn("1, 2, 3", block)

    def test_assembly_regions_are_resolved(self):
        """Additional assembly regions resolve through named part-region occurrences."""
        project = _project()
        part = project.parts[0]
        instance = project.assembly.instances[0]
        part_node_set, part_element_set, part_surface = part.regions

        project.assembly.regions.extend(
            (
                Region(
                    name="ASM_NODES",
                    scope=RegionScope.ASSEMBLY,
                    definition=named_region_definition(part_node_set, instance),
                    preferred_projection=RegionProjection.NODES,
                ),
                Region(
                    name="ASM_ELEMENTS",
                    scope=RegionScope.ASSEMBLY,
                    definition=named_region_definition(part_element_set, instance),
                    preferred_projection=RegionProjection.ELEMENTS,
                ),
                Region(
                    name="ASM_SURFACE",
                    scope=RegionScope.ASSEMBLY,
                    definition=named_region_definition(part_surface, instance),
                    preferred_projection=RegionProjection.FACETS,
                ),
            )
        )
        project.rebuild_index(strict=True)

        deck = FEMasterAdapter().write_deck_text(project, project.analyses[0])
        self.assertIn("*NSET, NSET=ASM_NODES\n1\n2\n3", deck)
        self.assertIn("*ELSET, ELSET=ASM_ELEMENTS\n1", deck)
        self.assertIn("*SURFACE, NAME=ASM_SURFACE\n3, 1, S1", deck)

    def test_amplitude_is_defined_before_and_referenced_by_load(self):
        project = _project()
        amplitude = Amplitude(
            name="RAMP",
            points=[(0.0, 0.0), (0.25, 1.0), (1.0, 1.0)],
        )
        project.amplitudes.append(amplitude)
        project.loads[0].amplitude_ref = EntityRef.of(amplitude)
        project.rebuild_index(strict=True)

        deck = FEMasterAdapter().write_deck_text(project, project.analyses[0])

        self.assertFalse(validate_deck(deck))
        self.assertIn("*AMPLITUDE, NAME=RAMP, TYPE=LINEAR", deck)
        self.assertIn("0, 0\n0.25, 1\n1, 1", deck)
        self.assertIn("AMPLITUDE=RAMP", deck)
        self.assertLess(deck.index("*AMPLITUDE"), deck.index("*CLOAD"))


def _project():
    """Build one canonical current-schema project used by FEMaster regressions."""
    project = Project(name="TEST")
    material = Material(
        name="STEEL",
        behaviors=[
            IsotropicElasticity(youngs_modulus=210000.0, poisson_ratio=0.3)
        ],
    )
    section = SolidSection(name="SOLID", material_ref=EntityRef.of(material))
    project.materials.append(material)
    project.sections.append(section)

    part = Part(name="P")
    part.mesh.nodes = NodeTable(
        ids=[1, 2, 3, 4],
        coordinates=[(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)],
    )
    part.mesh.element_blocks = [
        ElementBlock(
            definition=TetrahedronElementDefinition(name="Tetrahedra"),
            ids=[1],
            connectivity=[(1, 2, 3, 4)],
        )
    ]
    part.mesh.entity_nodes = {"Face-1": [1, 2, 3], "Cell-1": [1, 2, 3, 4]}
    part.mesh.entity_elements = {"Cell-1": [1]}
    part.mesh.entity_facets = {"Face-1": [(1, "S1")]}

    part_node_set = Region(
        name="FACE_NODES",
        definition=definition_from_local_labels(part, ["Face-1"]),
        preferred_projection=RegionProjection.NODES,
    )
    part_element_set = Region(
        name="CELL_ELEMENTS",
        definition=definition_from_local_labels(part, ["Cell-1"]),
        preferred_projection=RegionProjection.ELEMENTS,
    )
    part_surface = Region(
        name="PRESSURE",
        definition=definition_from_local_labels(part, ["Face-1"]),
        preferred_projection=RegionProjection.FACETS,
    )
    part.regions = [part_node_set, part_element_set, part_surface]
    part.section_assignments = [
        SectionAssignment(
            name="Section Assignment",
            section_ref=EntityRef.of(section),
            target=named_region_definition(part_element_set),
        )
    ]
    project.parts.append(part)

    instance = Instance(name="P-1", part_ref=EntityRef.of(part))
    project.assembly.instances.append(instance)
    assembly_node_set = Region(
        name="FACE_NODES",
        scope=RegionScope.ASSEMBLY,
        definition=named_region_definition(part_node_set, instance),
        preferred_projection=RegionProjection.NODES,
    )
    assembly_element_set = Region(
        name="CELL_ELEMENTS",
        scope=RegionScope.ASSEMBLY,
        definition=named_region_definition(part_element_set, instance),
        preferred_projection=RegionProjection.ELEMENTS,
    )
    assembly_surface = Region(
        name="PRESSURE",
        scope=RegionScope.ASSEMBLY,
        definition=named_region_definition(part_surface, instance),
        preferred_projection=RegionProjection.FACETS,
    )
    project.assembly.regions.extend(
        (assembly_node_set, assembly_element_set, assembly_surface)
    )

    support = FixedSupport(
        name="BC",
        target=named_region_definition(assembly_node_set),
    )
    load = ForceLoad(
        name="FORCE",
        target=named_region_definition(assembly_node_set),
        magnitude=1.0,
    )
    project.supports.append(support)
    project.loads.append(load)

    step = AnalysisStep(
        name="STEP",
        step_type="Linear Static",
        load_refs=[EntityRef.of(load)],
        support_refs=[EntityRef.of(support)],
    )
    project.steps.append(step)
    analysis = Analysis(name="STATIC", analysis_type="Linear Static")
    analysis.bind_steps([step])
    project.analyses.append(analysis)
    project.rebuild_index(strict=True)
    return project


if __name__ == "__main__":
    unittest.main()
