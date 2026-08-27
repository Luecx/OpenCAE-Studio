from __future__ import annotations

from opencae.model.core import EntityRef
from opencae.model.entities.regions import Region
from opencae.model.selection import (
    GeometryOperand,
    MeshFacetOperand,
    MeshNodeOperand,
    NamedRegionOperand,
    ReferencePointOperand,
    RegionDefinition,
    RegionProjection,
    RegionRequirement,
    RegionResolver,
    RegionSelectionItem,
)


def test_definition_deduplicates_same_occurrence_but_keeps_instances(project_factory):
    data = project_factory()
    part, first, second = data["part"], data["instance_1"], data["instance_2"]
    one = GeometryOperand(EntityRef.of(part, "Part"), 0, 1, EntityRef.of(first, "Instance"))
    duplicate = GeometryOperand(EntityRef.of(part, "Part"), 0, 1, EntityRef.of(first, "Instance"))
    other_instance = GeometryOperand(EntityRef.of(part, "Part"), 0, 1, EntityRef.of(second, "Instance"))
    definition = RegionDefinition(tuple(RegionSelectionItem(value) for value in (one, duplicate, other_instance)))
    assert len(definition.items) == 2


def test_geometry_projects_to_nodes_elements_and_facets(project_factory):
    data = project_factory()
    project, part, instance = data["project"], data["part"], data["instance_1"]
    resolver = RegionResolver(project)
    vertex = RegionDefinition((RegionSelectionItem(GeometryOperand(EntityRef.of(part, "Part"), 0, 1, EntityRef.of(instance, "Instance"))),))
    face = RegionDefinition((RegionSelectionItem(GeometryOperand(EntityRef.of(part, "Part"), 2, 1, EntityRef.of(instance, "Instance"))),))
    cell = RegionDefinition((RegionSelectionItem(GeometryOperand(EntityRef.of(part, "Part"), 3, 1, EntityRef.of(instance, "Instance"))),))
    assert resolver.resolve(vertex, RegionRequirement(RegionProjection.NODES, (0,), 1)).count(RegionProjection.NODES) == 1
    assert resolver.resolve(face, RegionRequirement(RegionProjection.NODES, (2,), 1)).count(RegionProjection.NODES) == 3
    facets = resolver.resolve(face, RegionRequirement(RegionProjection.FACETS, (2,), 1))
    assert facets.valid and {(item.element_id, item.local_face) for item in facets.facets} == {(1, "S1")}
    elements = resolver.resolve(cell, RegionRequirement(RegionProjection.ELEMENTS, (3,), 1))
    assert elements.valid and {item.element_id for item in elements.elements} == {1}


def test_named_part_region_is_occurrence_specific(project_factory):
    data = project_factory()
    project, region = data["project"], data["vertex_region"]
    definitions = []
    for instance in (data["instance_1"], data["instance_2"]):
        definitions.append(RegionDefinition((RegionSelectionItem(NamedRegionOperand(EntityRef.of(region, "Region"), EntityRef.of(instance, "Instance"))),)))
    occurrences = [RegionResolver(project).resolve(value, RegionRequirement(RegionProjection.NODES)) for value in definitions]
    assert {next(iter(value.nodes)).instance_id for value in occurrences} == {data["instance_1"].id, data["instance_2"].id}


def test_stale_mesh_selection_is_rejected(project_factory):
    data = project_factory()
    definition = RegionDefinition((RegionSelectionItem(MeshNodeOperand(EntityRef.of(data["part"], "Part"), 1, EntityRef.of(data["instance_1"], "Instance"), "old-mesh")),))
    result = RegionResolver(data["project"]).resolve(definition, RegionRequirement(RegionProjection.NODES))
    assert not result.valid
    assert {item.code for item in result.diagnostics} == {"stale_mesh_selection", "too_few_members"}


def test_invalid_mesh_facet_is_rejected(project_factory):
    data = project_factory()
    definition = RegionDefinition((RegionSelectionItem(MeshFacetOperand(EntityRef.of(data["part"], "Part"), 1, "S99", EntityRef.of(data["instance_1"], "Instance"), "mesh-r1")),))
    result = RegionResolver(data["project"]).resolve(definition, RegionRequirement(RegionProjection.FACETS))
    assert not result.valid
    assert "invalid_element_face" in {item.code for item in result.diagnostics}


def test_part_reference_point_requires_occurrence(project_factory):
    data = project_factory()
    definition = RegionDefinition((RegionSelectionItem(ReferencePointOperand(EntityRef.of(data["part_rp"], "ReferencePoint"))),))
    result = RegionResolver(data["project"]).resolve(definition, RegionRequirement(RegionProjection.NODES))
    assert not result.valid
    assert "missing_occurrence" in {item.code for item in result.diagnostics}


def test_named_region_cycles_are_reported(project_factory):
    data = project_factory()
    first = Region(name="A")
    second = Region(name="B")
    first.definition = RegionDefinition((RegionSelectionItem(NamedRegionOperand(EntityRef.of(second, "Region"))),))
    second.definition = RegionDefinition((RegionSelectionItem(NamedRegionOperand(EntityRef.of(first, "Region"))),))
    data["project"].assembly.regions.extend((first, second))
    data["project"].rebuild_index()
    result = RegionResolver(data["project"]).resolve(first.definition, RegionRequirement(RegionProjection.NODES))
    assert "region_cycle" in {item.code for item in result.diagnostics}


def test_reverse_reference_index_scans_region_definitions(project_factory):
    data = project_factory()
    uses = data["project"].references_to(data["vertex_region"].id)
    assert any(use.source_id == data["cload"].id and "target" in use.field_path for use in uses)


def test_context_picker_reselects_mesh_point_mode_for_mixed_policy():
    from opencae.model.selection import SelectableKind, SelectionPolicy
    from opencae.ui.viewport.context_pick import ContextPickManager

    class Message:
        def emit(self, _value): pass

    class Toolbar:
        def set_selection_enabled(self, *_args): pass

    class Owner:
        display_mode = "geometry"
        selection_mode = "auto"
        message = Message()
        toolbar = Toolbar()
        def set_selection_mode(self, mode): self.selection_mode = mode

    owner = Owner()
    manager = ContextPickManager(owner)
    policy = SelectionPolicy.create({
        SelectableKind.GEOMETRY_VERTEX,
        SelectableKind.GEOMETRY_FACE,
        SelectableKind.MESH_NODE,
        SelectableKind.MESH_ELEMENT,
    })
    manager.begin(policy, lambda _value: None)
    assert owner.selection_mode == "auto"
    owner.display_mode = "mesh"
    manager.refresh_for_display()
    assert owner.selection_mode == "point"


def test_mesh_facet_projects_only_its_local_nodes(project_factory):
    data = project_factory(include_constraints=False)
    part, instance = data["part"], data["instance_1"]
    definition = RegionDefinition((RegionSelectionItem(
        MeshFacetOperand(EntityRef.of(part, "Part"), 1, "S2", EntityRef.of(instance, "Instance"), part.mesh.revision)
    ),))
    resolved = RegionResolver(data["project"]).resolve(
        definition,
        RegionRequirement(RegionProjection.NODES, (0, 1, 2, 3), 1),
    )
    assert resolved.valid
    assert {item.node_id for item in resolved.nodes} == {1, 2, 4}


def test_whole_model_expands_all_active_occurrences(project_factory):
    from opencae.model.selection import WholeModelOperand

    data = project_factory(include_constraints=False)
    definition = RegionDefinition((RegionSelectionItem(WholeModelOperand()),))
    resolved = RegionResolver(data["project"]).resolve(
        definition,
        RegionRequirement(RegionProjection.ELEMENTS, (0, 1, 2, 3), 1),
    )
    assert resolved.valid
    assert {(item.instance_id, item.element_id) for item in resolved.elements} == {
        (data["instance_1"].id, 1),
        (data["instance_2"].id, 1),
    }


def test_unique_occurrence_requirement_rejects_mixed_instances(project_factory):
    data = project_factory(include_constraints=False)
    part = data["part"]
    definition = RegionDefinition(tuple(RegionSelectionItem(
        MeshNodeOperand(EntityRef.of(part, "Part"), 1, EntityRef.of(instance, "Instance"), part.mesh.revision)
    ) for instance in (data["instance_1"], data["instance_2"])))
    resolved = RegionResolver(data["project"]).resolve(
        definition,
        RegionRequirement(RegionProjection.NODES, (0, 1, 2, 3), 1, require_unique_occurrence=True),
    )
    assert not resolved.valid
    assert any(item.code == "multiple_occurrences" for item in resolved.diagnostics)


def test_picked_position_survives_project_roundtrip(project_factory):
    from opencae.persistence.project_codec import project_from_dict, project_to_dict

    data = project_factory(include_constraints=False)
    load = data["cload"]
    first = load.target.items[0]
    load.target = RegionDefinition((RegionSelectionItem(first.operand, (1.25, 2.5, 3.75), "picked"),))
    decoded = project_from_dict(project_to_dict(data["project"]))
    item = decoded.loads[0].target.items[0]
    assert item.picked_position == (1.25, 2.5, 3.75)
    assert item.display_label == "picked"


def test_stale_geometry_revision_is_reported(project_factory):
    from opencae.geometry.fingerprint import part_fingerprint

    data = project_factory(include_constraints=False)
    part, instance = data["part"], data["instance_1"]
    revision = part_fingerprint(part, include_mesh=False)
    operand = GeometryOperand(
        EntityRef.of(part, "Part"), 0, 1, EntityRef.of(instance, "Instance"), revision
    )
    part.geometry_settings.tolerance *= 10.0
    data["project"].rebuild_index()
    resolved = RegionResolver(data["project"]).resolve(
        RegionDefinition((RegionSelectionItem(operand),)),
        RegionRequirement(RegionProjection.NODES, (0,), 1),
    )
    assert not resolved.valid
    assert any(item.code == "stale_geometry_selection" for item in resolved.diagnostics)


def test_part_local_reference_point_can_be_validated_before_instancing(project_factory):
    data = project_factory(include_constraints=False)
    definition = RegionDefinition((RegionSelectionItem(
        ReferencePointOperand(EntityRef.of(data["part_rp"], "ReferencePoint"))
    ),))
    requirement = RegionRequirement(RegionProjection.NODES, (0,), 1)
    rejected = RegionResolver(data["project"]).resolve(definition, requirement)
    accepted = RegionResolver(data["project"]).resolve(definition, requirement, allow_part_local=True)
    assert not rejected.valid
    assert accepted.valid and len(accepted.reference_points) == 1


def test_persisted_geometry_facet_association_is_preferred(project_factory):
    data = project_factory(include_constraints=False)
    part, instance = data["part"], data["instance_1"]
    part.mesh.entity_facets["Face-1"] = [(1, "S3")]
    definition = RegionDefinition((RegionSelectionItem(
        GeometryOperand(EntityRef.of(part, "Part"), 2, 1, EntityRef.of(instance, "Instance"))
    ),))
    resolved = RegionResolver(data["project"]).resolve(
        definition,
        RegionRequirement(RegionProjection.FACETS, (2,), 1),
    )
    assert {(item.element_id, item.local_face) for item in resolved.facets} == {(1, "S3")}


def test_viewport_hit_operation_does_not_change_occurrence_identity():
    from opencae.model.selection import SelectableKind, SelectionOperation, ViewportHit

    hit = ViewportHit(SelectableKind.MESH_NODE, instance_id="i", mesh_id=4)
    assert hit.with_operation(SelectionOperation.REMOVE).key == hit.key
    assert hit.with_operation(SelectionOperation.REMOVE).selection_operation == SelectionOperation.REMOVE


def test_geometry_face_without_persisted_facet_mapping_is_invalid(project_factory):
    data = project_factory(include_constraints=False)
    part, instance = data["part"], data["instance_1"]
    part.mesh.entity_facets.clear()
    definition = RegionDefinition((RegionSelectionItem(
        GeometryOperand(EntityRef.of(part, "Part"), 2, 1, EntityRef.of(instance, "Instance"))
    ),))
    resolved = RegionResolver(data["project"]).resolve(
        definition,
        RegionRequirement(RegionProjection.FACETS, (2,), 1),
    )
    assert not resolved.valid
    assert any(item.code == "missing_facet_association" for item in resolved.diagnostics)


def test_element_region_surface_removes_internal_facets():
    from opencae.model.entities.assembly import Assembly, Instance
    from opencae.model.entities.elements import ElementDefinition
    from opencae.model.entities.mesh import ElementBlock, MeshState, NodeTable
    from opencae.model.entities.parts import Part
    from opencae.model.entities.project import Project
    from opencae.model.selection import MeshElementOperand

    definition = ElementDefinition(name="C3D4", category="Solid Elements", topology="Tetrahedra", order="Linear", formulation="Standard")
    mesh = MeshState(
        nodes=NodeTable(
            ids=[1, 2, 3, 4, 5],
            coordinates=[(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 0, -1)],
        ),
        element_blocks=[ElementBlock(definition, [1, 2], [(1, 2, 3, 4), (1, 3, 2, 5)])],
        revision="mesh-r1",
    )
    part = Part(name="PART", mesh=mesh)
    instance = Instance(name="I1", part_ref=EntityRef.of(part, "Part"))
    project = Project(name="P", parts=[part], assembly=Assembly(name="A", instances=[instance]))
    target = RegionDefinition(tuple(RegionSelectionItem(
        MeshElementOperand(EntityRef.of(part, "Part"), element_id, EntityRef.of(instance, "Instance"), mesh.revision)
    ) for element_id in (1, 2)))
    resolved = RegionResolver(project).resolve(
        target,
        RegionRequirement(RegionProjection.FACETS, (2,), 1),
    )
    assert resolved.valid
    assert len(resolved.facets) == 6
    assert not ({(item.element_id, item.local_face) for item in resolved.facets} & {(1, "S1"), (2, "S1")})


def test_viewport_selection_rejects_untyped_legacy_values():
    import pytest
    from opencae.model.selection import ViewportSelection

    with pytest.raises(TypeError):
        ViewportSelection.from_hits(({"kind": "node"},))


def test_reference_point_only_policy_uses_point_picker_in_mesh_display():
    from types import SimpleNamespace
    from opencae.model.selection import RegionProjection, RegionRequirement, SelectableKind, SelectionPolicy
    from opencae.ui.viewport.context_pick import ContextPickManager

    class Owner:
        selection_mode = "auto"
        display_mode = "mesh"
        message = SimpleNamespace(emit=lambda *_: None)
        toolbar = SimpleNamespace(set_selection_enabled=lambda *_: None)
        def set_selection_mode(self, mode): self.selection_mode = mode

    owner = Owner()
    manager = ContextPickManager(owner)
    policy = SelectionPolicy.create(
        {SelectableKind.REFERENCE_POINT},
        multiple=False,
        requirement=RegionRequirement(RegionProjection.SINGLE_CONTROL_NODE, (0,), 1, 1),
    )
    manager.begin(policy, lambda _value: None)
    assert owner.selection_mode == "point"
