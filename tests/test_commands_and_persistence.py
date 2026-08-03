from __future__ import annotations

from copy import deepcopy

from opencae.model.core import EntityRef
from opencae.model.entities.regions import Region
from opencae.persistence.project_codec import project_from_dict, project_to_dict
from opencae.store.commands import CompositeCommand, UpdateFieldCommand, make_add_command, make_delete_command, make_replace_command


def test_commands_apply_and_undo_by_entity_id(project_factory):
    data = project_factory(include_constraints=False)
    project, part = data["project"], data["part"]
    region = Region(name="NEW")
    add = make_add_command(project, part.id, "regions", region)
    project = add.apply(project); project.rebuild_index()
    assert project.resolve(region.id).name == "NEW"
    replacement = deepcopy(project.resolve(region.id)); replacement.name = "RENAMED"
    replace = make_replace_command(project, part.id, "regions", replacement)
    project = replace.apply(project); project.rebuild_index()
    assert project.resolve(region.id).name == "RENAMED"
    project = replace.undo(project); project.rebuild_index()
    assert project.resolve(region.id).name == "NEW"
    delete = make_delete_command(project, part.id, "regions", region.id)
    project = delete.apply(project); project.rebuild_index()
    assert project.try_resolve(region.id) is None
    project = delete.undo(project); project.rebuild_index()
    assert project.resolve(region.id).name == "NEW"


def test_composite_field_updates_are_reversible(project_factory):
    data = project_factory(include_constraints=False)
    project, part = data["project"], data["part"]
    command = CompositeCommand((
        UpdateFieldCommand(part.id, "mesh.status", part.mesh.status, "Outdated"),
        UpdateFieldCommand(part.id, "mesh.revision", part.mesh.revision, "mesh-r2"),
    ))
    project = command.apply(project); project.rebuild_index()
    assert part.mesh.status == "Outdated" and part.mesh.revision == "mesh-r2"
    project = command.undo(project); project.rebuild_index()
    assert part.mesh.status == "Generated" and part.mesh.revision == "mesh-r1"


def test_schema_18_roundtrip_preserves_region_operands(project_factory):
    project = project_factory()["project"]
    encoded = project_to_dict(project)
    decoded = project_from_dict(encoded)
    assert decoded.schema_version == 18
    assert decoded.reference_errors == []
    assert decoded.loads[0].target == project.loads[0].target


def test_nested_collection_location_and_reference_replacement(project_factory):
    from opencae.model.core import entity_with_replaced_references
    from opencae.model.entities.mesh import EdgeSeed
    from opencae.model.selection import NamedRegionOperand, RegionDefinition, RegionSelectionItem
    from opencae.store.commands import entity_collection_location

    data = project_factory(include_constraints=False)
    project, part = data["project"], data["part"]
    seed = EdgeSeed(
        name="SEED",
        target=RegionDefinition((RegionSelectionItem(NamedRegionOperand(EntityRef.of(data["vertex_region"], "Region"))),)),
    )
    part.mesh.seeds.append(seed)
    project.rebuild_index()
    assert entity_collection_location(project, seed.id) == (part.id, "mesh.seeds")

    replacement = Region(name="REPLACEMENT")
    part.regions.append(replacement)
    project.rebuild_index()
    candidate, changed = entity_with_replaced_references(seed, data["vertex_region"].id, replacement)
    assert changed
    assert candidate.target.items[0].operand.region_ref.entity_id == replacement.id


def test_cloning_part_remaps_nested_region_references(project_factory):
    from opencae.model.core import clone_entity_graph
    from opencae.model.selection import NamedRegionOperand, RegionDefinition, RegionSelectionItem

    data = project_factory(include_constraints=False)
    part = data["part"]
    source_region = data["vertex_region"]
    nested = Region(
        name="NESTED",
        definition=RegionDefinition((RegionSelectionItem(NamedRegionOperand(EntityRef.of(source_region, "Region"))),)),
    )
    part.regions.append(nested)
    clone = clone_entity_graph(part)
    assert clone.id != part.id
    clone_source = next(item for item in clone.regions if item.name == source_region.name)
    clone_nested = next(item for item in clone.regions if item.name == nested.name)
    assert clone_nested.definition.items[0].operand.region_ref.entity_id == clone_source.id
    assert clone_nested.definition.items[0].operand.region_ref.entity_id != source_region.id
