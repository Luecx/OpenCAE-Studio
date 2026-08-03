from __future__ import annotations

import json
from pathlib import Path

import pytest

from opencae.model.core import (
    EntityRef,
    NodeSetTarget,
    RegionMemberRef,
    clone_entity_graph,
    compatible_replacements,
    delete_entity_graph,
    remove_entity,
    replace_references,
)
from opencae.model.entities.assembly import Instance
from opencae.model.entities.project import Project
from opencae.model.entities.parts import Part
from opencae.model.entities.regions import Region, SectionAssignment
from opencae.model.entities.resources import Material
from opencae.model.entities.supports import FixedSupport
from opencae.persistence.project_codec import project_from_dict, project_to_dict
from opencae.solvers.femaster import FEMasterAdapter
from tests.test_femaster_dsl import _project


def _has_key(value, key):
    if isinstance(value, dict):
        return key in value or any(_has_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_has_key(item, key) for item in value)
    return False


def test_entity_ids_are_immutable():
    project = _project()
    original = project.parts[0].id
    with pytest.raises(AttributeError, match="immutable"):
        project.parts[0].id = "different"
    assert project.parts[0].id == original


def test_rename_does_not_rewrite_references():
    project = _project()
    project.ensure_references(strict=True)
    material = project.materials[0]
    section = project.sections[0]
    original_ref = section.material_ref
    material.name = "RENAMED_STEEL"
    project.rebuild_index(strict=True)
    assert section.material_ref == original_ref
    assert project.resolve(section.material_ref) is material
    assert project_to_dict(project)["sections"][0]["material_ref"]["entity_id"] == material.id


def test_schema_11_name_references_are_migrated_and_removed():
    raw = project_to_dict(_project())
    raw.pop("schema_version", None)
    raw["assembly"]["instances"][0]["part_name"] = "P"
    raw["assembly"]["instances"][0].pop("part_ref", None)
    raw["sections"][0]["material_name"] = "STEEL"
    raw["sections"][0].pop("material_ref", None)
    assignment = raw["parts"][0]["section_assignments"][0]
    assignment["section_name"] = "SOLID"
    assignment["region_name"] = "CELL_ELEMENTS"
    assignment.pop("section_ref", None)
    assignment.pop("region_ref", None)
    for collector in (*raw["supports"], *raw["loads"]):
        collector["region_name"] = "FACE_NODES"
        collector.pop("target", None)
    step = raw["analyses"][0]["steps"][0]
    step["active_loads"] = ["FORCE"]
    step["active_supports"] = ["BC"]
    step.pop("load_refs", None)
    step.pop("support_refs", None)

    project = project_from_dict(raw)
    assert project.schema_version == 13
    assert not project.reference_errors
    encoded = project_to_dict(project)
    for legacy_key in (
        "part_name", "material_name", "profile_name", "section_name", "region_name",
        "orientation_name", "coordinate_system_name", "active_loads", "active_supports",
        "analysis_name", "job_name", "step_name",
    ):
        assert not _has_key(encoded, legacy_key)
    assert encoded["assembly"]["instances"][0]["part_ref"]["entity_id"]
    assert encoded["loads"][0]["target"]["__type__"] == "node_set_target"


def test_delivered_project_file_is_schema_13_and_reference_clean():
    path = Path(__file__).resolve().parents[1] / "project.ocae"
    project = project_from_dict(json.loads(path.read_text(encoding="utf-8")))
    assert project.schema_version == 13
    assert not project.reference_errors


def test_same_scope_legacy_name_ambiguity_is_reported():
    project = _project()
    project.assembly.node_sets.append(Region(name="FACE_NODES", region_type="Node Set", scope="Assembly"))
    project.supports = [FixedSupport(name="AMBIGUOUS", target=NodeSetTarget(ref=EntityRef(expected_type="NodeSet", legacy_name="FACE_NODES")))]
    with pytest.raises(ValueError, match="ambiguous"):
        project.ensure_references(strict=True)


def test_reverse_references_can_be_replaced_and_cascade_deleted():
    project = _project()
    project.ensure_references(strict=True)
    old = project.materials[0]
    replacement = Material(name="ALUMINUM")
    project.materials.append(replacement)
    project.rebuild_index(strict=True)
    assert project.references_to(old.id)
    changed = replace_references(project, old.id, replacement)
    assert changed == 1
    assert project.sections[0].material_ref.entity_id == replacement.id

    deleted = delete_entity_graph(project, replacement.id)
    assert replacement.id in deleted
    assert project.materials == [old]
    assert not project.sections
    assert not project.parts[0].section_assignments


def test_clone_entity_graph_remaps_internal_but_not_external_references():
    project = _project()
    project.ensure_references(strict=True)
    original = project.parts[0]
    cloned = clone_entity_graph(original)
    assert cloned.id != original.id
    assert cloned.element_sets[0].id != original.element_sets[0].id
    assert cloned.section_assignments[0].region_ref.entity_id == cloned.element_sets[0].id
    assert cloned.section_assignments[0].section_ref.entity_id == original.section_assignments[0].section_ref.entity_id


def test_store_selection_survives_undo_redo_by_id():
    pytest.importorskip("PyQt6")
    from opencae.store.project_store import ProjectStore
    project = _project()
    project.ensure_references(strict=True)
    store = ProjectStore(project)
    part_id = project.parts[0].id
    store.select(project.parts[0])
    store.mutate("Rename part", lambda current: setattr(current.parts[0], "name", "RENAMED"))
    assert store.selection.id == part_id
    store.undo()
    assert store.selection.id == part_id
    assert store.selection.name == "P"
    store.redo()
    assert store.selection.id == part_id
    assert store.selection.name == "RENAMED"


def test_specific_target_type_survives_roundtrip():
    project = _project()
    project.ensure_references(strict=True)
    encoded = project_to_dict(project)
    loaded = project_from_dict(encoded)
    assert isinstance(loaded.supports[0].target, NodeSetTarget)
    assert loaded.supports[0].target.ref.entity_id == loaded.assembly.node_sets[0].id


def test_multi_instance_assembly_set_is_merged_by_exported_ids():
    project = _project()
    part = project.parts[0]
    project.assembly.instances.append(Instance(name="P-2", part_ref=EntityRef.of(part, "Part")))
    both = Region(
        name="BOTH",
        region_type="Node Set",
        scope="Assembly",
        members=["P-1.Face-1", "P-2.Face-1"],
    )
    project.assembly.node_sets.append(both)
    project.ensure_references(strict=True)
    deck = FEMasterAdapter().write_deck_text(project, project.analyses[0])
    block = deck.split("*NSET, NSET=BOTH\n", 1)[1].split("*", 1)[0]
    assert [int(value) for value in block.split()] == [1, 2, 3, 5, 6, 7]


def test_direct_mesh_node_target_exports_an_internal_instance_set():
    from opencae.model.core import MeshNodeTarget
    project = _project()
    instance = project.assembly.instances[0]
    project.supports[0].target = MeshNodeTarget(EntityRef.of(instance, "Instance"), 2)
    project.ensure_references(strict=True)
    deck = FEMasterAdapter().write_deck_text(project, project.analyses[0])
    assert "*NSET, NSET=BC_TARGET\n2" in deck
    assert "*SUPPORT, SUPPORT_COLLECTOR=BC" in deck


def test_direct_mesh_element_target_uses_instance_element_mapping():
    from opencae.model.core import MeshElementTarget
    from opencae.model.entities.loads import VolumeLoad
    project = _project()
    part = project.parts[0]
    second = Instance(name="P-2", part_ref=EntityRef.of(part, "Part"))
    project.assembly.instances.append(second)
    load = VolumeLoad(name="DIRECT_ELEMENT", target=MeshElementTarget(EntityRef.of(second, "Instance"), 1), components=[1, 2, 3])
    project.loads.append(load)
    project.analyses[0].steps[0].load_refs.append(EntityRef.of(load, "Load"))
    project.ensure_references(strict=True)
    deck = FEMasterAdapter().write_deck_text(project, project.analyses[0])
    assert "*ELSET, ELSET=DIRECT_ELEMENT_TARGET\n2" in deck
    assert "DIRECT_ELEMENT_TARGET, 1, 2, 3" in deck


def test_project_index_includes_entities_nested_in_mesh_state():
    from opencae.model.mesh import DefaultSeed, ElementControl
    project = Project(name="Nested")
    part = Part(name="P")
    seed = DefaultSeed(name="Seed")
    control = ElementControl(name="Control")
    part.mesh.seeds.append(seed)
    part.mesh.element_controls.append(control)
    project.parts.append(part)
    project.rebuild_index()
    assert project.resolve(seed.id) is seed
    assert project.resolve(control.id) is control
    assert project.index.parent_id[seed.id] == part.id


def test_clone_part_remaps_nested_mesh_entity_ids_and_internal_references():
    from opencae.model.mesh import DefaultSeed
    part = Part(name="P")
    seed = DefaultSeed(name="Seed")
    part.mesh.seeds.append(seed)
    region = Region(name="E", region_type="ElementSet", members=["Element-1"])
    part.element_sets.append(region)
    assignment = SectionAssignment(name="A", region_ref=EntityRef.of(region), section_ref=EntityRef("external", "Section"))
    part.section_assignments.append(assignment)
    clone = clone_entity_graph(part)
    assert clone.id != part.id
    assert clone.mesh.seeds[0].id != seed.id
    assert clone.section_assignments[0].region_ref.entity_id == clone.element_sets[0].id
    assert clone.section_assignments[0].section_ref.entity_id == "external"


def test_validation_accepts_whole_model_inertia_target_without_entity_reference():
    from opencae.model.core import WholeModelTarget
    from opencae.model.entities.loads import InertiaLoad
    from opencae.model.validation import validate_project
    project = _project()
    project.loads = [InertiaLoad(name="I", target=WholeModelTarget())]
    project.analyses.clear()
    assert validate_project(project) == []


def test_validation_rejects_missing_direct_mesh_member():
    from opencae.model.core import MeshNodeTarget
    from opencae.model.validation import validate_project
    project = _project()
    instance = project.assembly.instances[0]
    project.supports = [FixedSupport(name="BC", target=MeshNodeTarget(EntityRef.of(instance), 999))]
    project.analyses.clear()
    errors = validate_project(project)
    assert any("node 999 does not exist" in item for item in errors)


def test_assembly_region_members_are_bound_to_instance_ids_and_survive_rename():
    project = _project()
    project.ensure_references(strict=True)
    instance = project.assembly.instances[0]
    member = project.assembly.node_sets[0].members[0]
    assert isinstance(member, RegionMemberRef)
    assert member.owner_ref.entity_id == instance.id

    instance.name = "RENAMED.INSTANCE"
    project.parts[0].name = "RENAMED_PART"
    project.rebuild_index(strict=True)
    deck = FEMasterAdapter().write_deck_text(project, project.analyses[0])
    block = deck.split("*NSET, NSET=FACE_NODES\n", 1)[1].split("*", 1)[0]
    assert [int(value) for value in block.split()] == [1, 2, 3]


def test_region_member_refs_are_persisted_in_schema_13():
    project = _project()
    project.ensure_references(strict=True)
    encoded = project_to_dict(project)
    member = encoded["assembly"]["node_sets"][0]["members"][0]
    assert encoded["schema_version"] == 13
    assert member["__type__"] == "region_member_ref"
    assert member["owner_ref"]["entity_id"] == project.assembly.instances[0].id
    loaded = project_from_dict(encoded)
    assert isinstance(loaded.assembly.node_sets[0].members[0], RegionMemberRef)


def test_remove_entity_supports_mesh_state_collections():
    from opencae.model.mesh import DefaultSeed
    project = Project(name="Nested")
    part = Part(name="P")
    seed = DefaultSeed(name="Seed")
    part.mesh.seeds.append(seed)
    project.parts.append(part)
    project.rebuild_index(strict=True)
    assert remove_entity(project, seed.id)
    assert part.mesh.seeds == []
    assert project.try_resolve(seed.id) is None


def test_compatible_replacements_use_typed_family_and_scope():
    from opencae.model.entities.loads import PressureLoad
    from opencae.model.core import SurfaceTarget

    project = _project()
    old_load = project.loads[0]
    candidate = PressureLoad(
        name="PRESSURE",
        target=SurfaceTarget(ref=EntityRef.of(project.assembly.surfaces[0], "Surface")),
        pressure=2.0,
    )
    project.loads.append(candidate)
    project.rebuild_index(strict=True)
    assert candidate in compatible_replacements(project, old_load)

    original_set = project.assembly.node_sets[0]
    same_scope = Region(name="OTHER", region_type="Node Set", scope="Assembly")
    wrong_kind = Region(name="SURFACE", region_type="Surface", scope="Assembly")
    part_scope = Region(name="PART_SET", region_type="Node Set")
    project.assembly.node_sets.append(same_scope)
    project.assembly.surfaces.append(wrong_kind)
    project.parts[0].node_sets.append(part_scope)
    project.rebuild_index(strict=True)
    replacements = compatible_replacements(project, original_set)
    assert same_scope in replacements
    assert wrong_kind not in replacements
    assert part_scope not in replacements


def test_geometry_and_mesh_targets_are_bound_to_part_owned_refs():
    from opencae.model.entities.geometry import PartitionEdgeFeature
    from opencae.model.mesh import EdgeSeed, ElementControl

    project = _project()
    part = project.parts[0]
    part.geometry.append(PartitionEdgeFeature(name="Partition", references=["Edge-4"], parameters={"vertices": ["Vertex-2"]}))
    part.mesh.seeds.append(EdgeSeed(name="Edge Seed", targets=["Edge-4"]))
    part.mesh.element_controls.append(ElementControl(name="Control", targets=["ElementSet:CELL_ELEMENTS"]))
    project.rebuild_index(strict=True)

    feature = part.geometry[-1]
    assert isinstance(feature.references[0], RegionMemberRef)
    assert feature.references[0].owner_ref.entity_id == part.id
    assert isinstance(feature.parameters["vertices"][0], RegionMemberRef)
    assert isinstance(part.mesh.seeds[-1].targets[0], RegionMemberRef)
    assert isinstance(part.mesh.element_controls[-1].targets[0], EntityRef)
    assert part.mesh.element_controls[-1].targets[0].entity_id == part.element_sets[0].id

    loaded = project_from_dict(project_to_dict(project))
    assert isinstance(loaded.parts[0].geometry[-1].references[0], RegionMemberRef)
    assert isinstance(loaded.parts[0].mesh.element_controls[-1].targets[0], EntityRef)
