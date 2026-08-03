from dataclasses import fields

from opencae.model import (
    EntityRef,
    Instance,
    InstanceEntityTarget,
    Part,
    Project,
    ReferencePoint,
    RegionMemberKind,
    RegionMemberRef,
    RegionMemberTarget,
    SectionAssignment,
    TargetKind,
    assembly_target_options,
    create_load,
    create_region,
    create_support,
)
from opencae.model.entities.constraints import (
    ConstraintReference,
    ConstraintReferenceKind,
    KinematicCoupling,
    TieConstraint,
    create_constraint,
)
from opencae.model.entities.elements import TetrahedronElementDefinition
from opencae.model.entities.mesh import ElementBlock, NodeTable
from opencae.model.entities.resources import Material
from opencae.model.entities.sections import SolidSection
from opencae.model.validation import validate_project
from opencae.persistence.migrations import migrate_project_data
from opencae.persistence.project_codec import project_from_dict, project_to_dict


def _project_with_mesh():
    part = Part(name="Part")
    part.mesh.nodes = NodeTable(
        ids=[1, 2, 3, 4],
        coordinates=[(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)],
    )
    part.mesh.element_blocks = [
        ElementBlock(
            definition=TetrahedronElementDefinition(name="Tet"),
            ids=[1],
            connectivity=[(1, 2, 3, 4)],
        )
    ]
    part.mesh.entity_nodes = {"Face-1": [1, 2, 3], "Cell-1": [1, 2, 3, 4]}
    part.mesh.entity_elements = {"Face-1": [1], "Cell-1": [1]}
    part.mesh.node_count = 4
    part.mesh.element_count = 1

    node_set = create_region(
        "Node Set",
        name="FIX",
        members=[RegionMemberRef(RegionMemberKind.FACE, EntityRef.of(part, "Part"), 1)],
    )
    surface = create_region(
        "Surface",
        name="PRESS",
        members=[RegionMemberRef(RegionMemberKind.FACE, EntityRef.of(part, "Part"), 1)],
    )
    element_set = create_region(
        "Element Set",
        name="SOLID",
        members=[RegionMemberRef(RegionMemberKind.CELL, EntityRef.of(part, "Part"), 1)],
    )
    rp = ReferencePoint(name="RP", position=(0, 0, 2))
    part.node_sets = [node_set]
    part.surfaces = [surface]
    part.element_sets = [element_set]
    part.reference_points = [rp]

    material = Material(name="M", youngs_modulus=210000, poisson_ratio=0.3)
    section = SolidSection(name="S", material_ref=EntityRef.of(material, "Material"))
    part.section_assignments = [
        SectionAssignment(
            name="Assign",
            section_ref=EntityRef.of(section, "Section"),
            target=RegionMemberTarget(
                TargetKind.ELEMENT_SET,
                RegionMemberRef(RegionMemberKind.CELL, EntityRef.of(part, "Part"), 1),
            ),
        )
    ]
    instance = Instance(name="I", part_ref=EntityRef.of(part, "Part"))
    project = Project(name="P", parts=[part], materials=[material], sections=[section])
    project.assembly.instances = [instance]
    project.rebuild_index()
    return project, part, instance, node_set, surface, element_set, rp


def test_part_targets_are_projected_through_instances_and_rename_safe():
    project, _part, instance, node_set, _surface, _element_set, rp = _project_with_mesh()
    options = assembly_target_options(project, TargetKind.NODE_SET)
    by_label = dict(options)
    assert isinstance(by_label["I.FIX"], InstanceEntityTarget)
    assert isinstance(by_label["I.RP"], InstanceEntityTarget)

    support = create_support("Fixed", name="Support", target=by_label["I.FIX"])
    project.supports.append(support)
    project.rebuild_index()
    assert project.references_to(instance.id)
    assert project.references_to(node_set.id)

    instance.name = "RenamedInstance"
    node_set.name = "RenamedSet"
    rp.name = "RenamedRP"
    labels = {label for label, _target in assembly_target_options(project, TargetKind.NODE_SET)}
    assert "RenamedInstance.RenamedSet" in labels
    assert "RenamedInstance.RenamedRP" in labels
    assert support.target.instance_ref.entity_id == instance.id
    assert support.target.entity_ref.entity_id == node_set.id


def test_direct_targets_and_instance_targets_roundtrip():
    project, part, instance, node_set, surface, _element_set, rp = _project_with_mesh()
    project.supports.append(
        create_support(
            "Fixed",
            name="DirectFaceSupport",
            target=RegionMemberTarget(
                TargetKind.NODE_SET,
                RegionMemberRef(RegionMemberKind.FACE, EntityRef.of(instance, "Instance"), 1),
            ),
        )
    )
    project.loads.extend(
        [
            create_load(
                "Pressure",
                name="ProjectedPressure",
                target=InstanceEntityTarget(
                    TargetKind.SURFACE,
                    EntityRef.of(instance, "Instance"),
                    EntityRef.of(surface, "Surface"),
                ),
                pressure=2.0,
            ),
            create_load(
                "Concentrated Load",
                name="ProjectedRP",
                target=InstanceEntityTarget(
                    TargetKind.REFERENCE_POINT,
                    EntityRef.of(instance, "Instance"),
                    EntityRef.of(rp, "ReferencePoint"),
                ),
                components=[1, 0, 0, 0, 0, 0],
            ),
        ]
    )
    project.rebuild_index()
    clone = project_from_dict(project_to_dict(project))
    assert clone.schema_version == 14
    assert isinstance(clone.supports[0].target, RegionMemberTarget)
    assert isinstance(clone.loads[0].target, InstanceEntityTarget)
    assert isinstance(clone.parts[0].section_assignments[0].target, RegionMemberTarget)
    assert clone.reference_errors == []


def test_femaster_export_handles_direct_faces_projected_sets_rps_and_couplings():
    project, _part, instance, node_set, surface, _element_set, rp = _project_with_mesh()
    project.supports.append(
        create_support(
            "Fixed",
            name="DirectFaceSupport",
            target=RegionMemberTarget(
                TargetKind.NODE_SET,
                RegionMemberRef(RegionMemberKind.FACE, EntityRef.of(instance, "Instance"), 1),
            ),
        )
    )
    project.loads.append(
        create_load(
            "Pressure",
            name="Pressure",
            target=InstanceEntityTarget(
                TargetKind.SURFACE,
                EntityRef.of(instance, "Instance"),
                EntityRef.of(surface, "Surface"),
            ),
            pressure=2.0,
        )
    )
    project.assembly.constraints.append(
        create_constraint(
            "Kinematic Coupling",
            name="Coupling",
            master=ConstraintReference(
                ConstraintReferenceKind.REFERENCE_POINT,
                EntityRef.of(rp, "ReferencePoint"),
                EntityRef.of(instance, "Instance"),
            ),
            slave=ConstraintReference(
                ConstraintReferenceKind.NODE_SET,
                EntityRef.of(node_set, "NodeSet"),
                EntityRef.of(instance, "Instance"),
            ),
            components=(1, 1, 1, 0, 0, 0),
        )
    )
    project.rebuild_index()
    assert validate_project(project) == []
    deck = project.render_deck("FEMaster")
    assert "*NSET, NSET=NODE_SET_FACE_1" in deck
    assert "*SURFACE, NAME=I_PRESS" in deck
    assert "*COUPLING, MASTER=I_RP_RP, TYPE=KINEMATIC, SLAVE=I_FIX" in deck
    assert "ADJUST=" not in deck
    assert "DISTANCE=" not in deck


def test_adjust_and_distance_only_exist_on_tie_constraints():
    kinematic_fields = {item.name for item in fields(KinematicCoupling)}
    tie_fields = {item.name for item in fields(TieConstraint)}
    assert "adjust" not in kinematic_fields
    assert "distance" not in kinematic_fields
    assert {"adjust", "distance"} <= tie_fields


def test_schema_13_section_assignments_migrate_to_typed_targets():
    data = {
        "__type__": "project",
        "schema_version": 13,
        "id": "project-1",
        "name": "P",
        "parts": [
            {
                "__type__": "part",
                "id": "part-1",
                "name": "Part",
                "section_assignments": [
                    {
                        "__type__": "section_assignment",
                        "id": "assignment-1",
                        "name": "Assign",
                        "section_ref": {
                            "__type__": "entity_ref",
                            "entity_id": "section-1",
                            "expected_type": "Section",
                            "legacy_name": "",
                        },
                        "region_ref": {
                            "__type__": "entity_ref",
                            "entity_id": "set-1",
                            "expected_type": "ElementSet",
                            "legacy_name": "",
                        },
                    }
                ],
            }
        ],
    }
    migrated, report = migrate_project_data(data)
    assignment = migrated["parts"][0]["section_assignments"][0]
    assert migrated["schema_version"] == 14
    assert "region_ref" not in assignment
    assert assignment["target"]["__type__"] == "element_set_target"
    assert assignment["target"]["ref"]["entity_id"] == "set-1"
    assert report.migrated


def test_full_schema_13_project_loads_and_binds_section_target():
    project, _part, _instance, _node_set, _surface, element_set, _rp = _project_with_mesh()
    data = project_to_dict(project)
    data["schema_version"] = 13
    assignment = data["parts"][0]["section_assignments"][0]
    assignment.pop("target")
    assignment["region_ref"] = {
        "__type__": "entity_ref",
        "entity_id": element_set.id,
        "expected_type": "ElementSet",
        "legacy_name": "",
    }
    loaded = project_from_dict(data)
    target = loaded.parts[0].section_assignments[0].target
    assert target.ref.entity_id == element_set.id
    assert loaded.reference_errors == []


def test_part_clone_remaps_direct_section_target_owner():
    from opencae.model.core import clone_entity_graph

    _project, part, _instance, _node_set, _surface, _element_set, _rp = _project_with_mesh()
    clone = clone_entity_graph(part)
    assert clone.id != part.id
    target = clone.section_assignments[0].target
    assert isinstance(target, RegionMemberTarget)
    assert target.member.owner_ref.entity_id == clone.id


def test_single_mesh_element_can_be_used_as_section_target():
    from opencae.model import MeshElementTarget

    project, part, _instance, _node_set, _surface, _element_set, _rp = _project_with_mesh()
    part.section_assignments[0].target = MeshElementTarget(EntityRef.of(part, "Part"), 1)
    project.rebuild_index()
    assert validate_project(project) == []
    deck = project.render_deck("FEMaster")
    assert "*ELSET, ELSET=ELEMENT_SET_ELEMENT_1" in deck
    assert "*SOLIDSECTION, ELSET=ELEMENT_SET_ELEMENT_1" in deck


def test_legacy_coupling_tie_parameters_are_ignored():
    coupling = create_constraint(
        "Kinematic Coupling",
        name="Legacy",
        adjust=True,
        distance=1.5,
    )
    assert isinstance(coupling, KinematicCoupling)
    assert not hasattr(coupling, "adjust")
    assert not hasattr(coupling, "distance")


def test_tie_uses_surface_master_and_slave_and_keeps_tie_parameters():
    project, _part, instance, _node_set, surface, _element_set, _rp = _project_with_mesh()
    reference = lambda: ConstraintReference(
        ConstraintReferenceKind.SURFACE,
        EntityRef.of(surface, "Surface"),
        EntityRef.of(instance, "Instance"),
    )
    project.assembly.constraints.append(
        create_constraint(
            "Tie",
            name="Tie",
            master=reference(),
            slave=reference(),
            adjust=True,
            distance=0.25,
        )
    )
    project.rebuild_index()
    deck = project.render_deck("FEMaster")
    assert "*TIE, MASTER=I_PRESS, SLAVE=I_PRESS, ADJUST=ON, DISTANCE=0.25" in deck
