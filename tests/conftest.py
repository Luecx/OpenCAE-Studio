from __future__ import annotations

import pytest

from opencae.model.core import EntityRef
from opencae.model.entities.analysis import AnalysisStep, LinearStaticAnalysis
from opencae.model.entities.assembly import Assembly, Instance
from opencae.model.entities.constraints import KinematicCoupling, TieConstraint
from opencae.model.entities.elements import ElementDefinition
from opencae.model.entities.loads import ConcentratedLoad, PressureLoad
from opencae.model.entities.mesh import (
    ElementBlock,
    MeshState,
    MeshStatus,
    NodeTable,
)
from opencae.model.entities.parts import Part
from opencae.model.entities.project import Project
from opencae.model.entities.regions import ReferencePoint, Region, SectionAssignment
from opencae.model.entities.resources import Material
from opencae.model.entities.sections import SolidSection
from opencae.model.entities.supports import FixedSupport
from opencae.model.selection import (
    GeometryOperand,
    MeshFacetOperand,
    MeshNodeOperand,
    NamedRegionOperand,
    NodalLoadDistribution,
    ReferencePointOperand,
    RegionDefinition,
    RegionProjection,
    RegionScope,
    RegionSelectionItem,
)


def definition(*operands):
    return RegionDefinition(tuple(RegionSelectionItem(item) for item in operands))


def geometry(part, dimension, tag, instance=None):
    return GeometryOperand(
        EntityRef.of(part, "Part"),
        dimension,
        tag,
        EntityRef.of(instance, "Instance") if instance else None,
    )


@pytest.fixture
def project_factory():
    def create(*, two_instances=True, include_constraints=True):
        element = ElementDefinition(
            name="C3D4",
            category="Solid Elements",
            topology="Tetrahedra",
            order="Linear",
            formulation="Standard",
        )
        mesh = MeshState(
            nodes=NodeTable(
                ids=[1, 2, 3, 4],
                coordinates=[
                    (0.0, 0.0, 0.0),
                    (1.0, 0.0, 0.0),
                    (0.0, 1.0, 0.0),
                    (0.0, 0.0, 1.0),
                ],
            ),
            element_blocks=[ElementBlock(element, [1], [(1, 2, 3, 4)])],
            entity_nodes={
                "Vertex-1": [1],
                "Vertex-2": [2],
                "Edge-1": [1, 2],
                "Face-1": [1, 2, 3],
                "Cell-1": [1, 2, 3, 4],
            },
            entity_elements={
                "Edge-1": [1],
                "Face-1": [1],
                "Cell-1": [1],
            },
            entity_facets={"Face-1": [(1, "S1")]},
            node_count=4,
            element_count=1,
            mesh_dimension=3,
            status=MeshStatus.CURRENT,
            revision="mesh-r1",
        )
        part_rp = ReferencePoint(name="PART_RP", position=(0.25, 0.25, 0.25), scope="Part")
        part = Part(name="PART", mesh=mesh, reference_points=[part_rp])
        vertex_region = Region(
            name="VERTEX_SET",
            scope=RegionScope.PART,
            definition=definition(geometry(part, 0, 1)),
            preferred_projection=RegionProjection.NODES,
        )
        face_region = Region(
            name="FACE_REGION",
            scope=RegionScope.PART,
            definition=definition(geometry(part, 2, 1)),
            preferred_projection=RegionProjection.FACETS,
        )
        cell_region = Region(
            name="CELL_REGION",
            scope=RegionScope.PART,
            definition=definition(geometry(part, 3, 1)),
            preferred_projection=RegionProjection.ELEMENTS,
        )
        part.regions.extend((vertex_region, face_region, cell_region))

        instance_1 = Instance(name="I1", part_ref=EntityRef.of(part, "Part"))
        instances = [instance_1]
        instance_2 = None
        if two_instances:
            instance_2 = Instance(
                name="I2",
                part_ref=EntityRef.of(part, "Part"),
                translation=(2.0, 0.0, 0.0),
            )
            instances.append(instance_2)
        assembly_rp = ReferencePoint(name="ASSEMBLY_RP", position=(0.0, 0.0, 0.0), scope="Assembly")
        assembly = Assembly(name="ASSEMBLY", instances=instances, reference_points=[assembly_rp])

        material = Material(name="STEEL", youngs_modulus=210000.0, poisson_ratio=0.3)
        section = SolidSection(name="SOLID", material_ref=EntityRef.of(material, "Material"))
        assignment = SectionAssignment(
            name="SECTION_ASSIGNMENT",
            section_ref=EntityRef.of(section, "Section"),
            target=definition(geometry(part, 3, 1)),
        )
        part.section_assignments.append(assignment)

        support = FixedSupport(
            name="FIXED",
            target=definition(geometry(part, 2, 1, instance_1)),
        )
        cload = ConcentratedLoad(
            name="CLOAD",
            target=definition(
                NamedRegionOperand(EntityRef.of(vertex_region, "Region"), EntityRef.of(instance_1, "Instance")),
                MeshNodeOperand(EntityRef.of(part, "Part"), 2, EntityRef.of(instance_1, "Instance"), mesh.revision),
            ),
            components=[100.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            distribution=NodalLoadDistribution.TOTAL_UNIFORM,
        )
        pressure = PressureLoad(
            name="PRESSURE",
            target=definition(geometry(part, 2, 1, instance_1)),
            pressure=2.5,
        )

        if include_constraints:
            coupling = KinematicCoupling(
                name="COUPLING",
                control_point=definition(geometry(part, 0, 1, instance_1)),
                slave=definition(geometry(part, 2, 1, instance_1)),
            )
            tie = TieConstraint(
                name="TIE",
                master=definition(geometry(part, 2, 1, instance_1)),
                slave=definition(MeshFacetOperand(EntityRef.of(part, "Part"), 1, "S2", EntityRef.of(instance_1, "Instance"), mesh.revision)),
                adjust=True,
                distance=0.1,
            )
            assembly.constraints.extend((coupling, tie))
        else:
            coupling = tie = None

        step = AnalysisStep(
            name="STEP",
            step_type="Linear Static",
            load_refs=[EntityRef.of(cload, "Load"), EntityRef.of(pressure, "Load")],
            support_refs=[EntityRef.of(support, "Support")],
        )
        analysis = LinearStaticAnalysis(name="ANALYSIS", steps=[step])
        project = Project(
            name="TEST",
            parts=[part],
            assembly=assembly,
            supports=[support],
            loads=[cload, pressure],
            materials=[material],
            sections=[section],
            analyses=[analysis],
        )
        return {
            "project": project,
            "part": part,
            "instance_1": instance_1,
            "instance_2": instance_2,
            "vertex_region": vertex_region,
            "face_region": face_region,
            "cell_region": cell_region,
            "part_rp": part_rp,
            "assembly_rp": assembly_rp,
            "support": support,
            "cload": cload,
            "pressure": pressure,
            "coupling": coupling,
            "tie": tie,
            "material": material,
            "section": section,
            "assignment": assignment,
            "analysis": analysis,
        }
    return create
