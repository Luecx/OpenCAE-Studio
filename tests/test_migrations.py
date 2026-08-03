from __future__ import annotations

from copy import deepcopy

from opencae.model.entities.mesh import EdgeSeed, ElementControl
from opencae.model.selection import GeometryOperand, MeshElementOperand
from opencae.persistence.migrations import migrate_project_data
from opencae.persistence.project_codec import project_from_dict, project_to_dict


def test_schema_14_meshing_targets_migrate_to_region_definitions(project_factory):
    data = project_factory(include_constraints=False)
    part = data["part"]
    part.mesh.seeds.append(EdgeSeed(name="EDGE_SEED"))
    part.mesh.element_controls.append(ElementControl(name="ELEMENT_CONTROL"))
    data["project"].rebuild_index()
    encoded = project_to_dict(data["project"])
    encoded["schema_version"] = 14
    mesh = encoded["parts"][0]["mesh"]
    seed = mesh["seeds"][0]
    seed.pop("target", None)
    seed["targets"] = ["Edge-1"]
    control = mesh["element_controls"][0]
    control.pop("target", None)
    control["targets"] = ["Element-1"]

    decoded = project_from_dict(encoded)
    assert decoded.schema_version == 18
    seed_operand = decoded.parts[0].mesh.seeds[0].target.items[0].operand
    control_operand = decoded.parts[0].mesh.element_controls[0].target.items[0].operand
    assert isinstance(seed_operand, GeometryOperand)
    assert seed_operand.dimension == 1 and seed_operand.tag == 1
    assert seed_operand.owner_ref.entity_id == decoded.parts[0].id
    assert isinstance(control_operand, MeshElementOperand)
    assert control_operand.element_id == 1


def test_schema_13_constraint_migration_removes_tie_fields_from_coupling(project_factory):
    encoded = project_to_dict(project_factory()["project"])
    encoded["schema_version"] = 13
    constraint = encoded["assembly"]["constraints"][0]
    control_point = constraint.pop("control_point")
    slave = constraint["slave"]
    # Recreate the schema-13 reference representation consumed by the migration.
    point_operand = control_point["items"]["__tuple__"][0]["operand"]
    slave_operand = slave["items"]["__tuple__"][0]["operand"]
    constraint["master"] = {
        "__type__": "constraint_reference",
        "kind": "Reference Point",
        "ref": point_operand.get("reference_point_ref") or point_operand.get("owner_ref"),
    }
    constraint["slave"] = {
        "__type__": "constraint_reference",
        "kind": "Node Set",
        "ref": slave_operand.get("region_ref") or slave_operand.get("owner_ref"),
    }
    constraint["adjust"] = True
    constraint["distance"] = 4.2

    migrated, report = migrate_project_data(deepcopy(encoded))
    current = migrated["assembly"]["constraints"][0]
    assert report.source_version == 13 and report.target_version == 18
    assert "control_point" in current and "slave" in current
    assert "master" not in current
    assert "adjust" not in current and "distance" not in current


def test_schema_13_unifies_region_collections(project_factory):
    encoded = project_to_dict(project_factory(include_constraints=False)["project"])
    encoded["schema_version"] = 13
    part = encoded["parts"][0]
    old_regions = part.pop("regions")
    part["node_sets"] = [old_regions[0]]
    part["element_sets"] = [old_regions[2]]
    part["surfaces"] = [old_regions[1]]
    for region in (*part["node_sets"], *part["element_sets"], *part["surfaces"]):
        region.pop("preferred_projection", None)

    migrated, _ = migrate_project_data(encoded)
    regions = migrated["parts"][0]["regions"]
    assert len(regions) == 3
    assert {item["preferred_projection"] for item in regions} == {"nodes", "elements", "facets"}
    assert all("node_sets" not in migrated["parts"][0] for _ in (0,))


def test_schema_16_geometry_feature_selections_migrate_to_region_definitions(project_factory):
    from opencae.model.geometry import PartitionEdgeFeature
    from opencae.model.selection import RegionDefinition, RegionSelectionItem
    from opencae.model.core import EntityRef

    data = project_factory(include_constraints=False)
    part = data["part"]
    feature = PartitionEdgeFeature(name="SPLIT", method="Vertex")
    part.geometry.append(feature)
    data["project"].rebuild_index()
    encoded = project_to_dict(data["project"])
    encoded["schema_version"] = 16
    item = encoded["parts"][0]["geometry"][-1]
    item.pop("target", None)
    item.pop("split_target", None)
    item.pop("method", None)
    item.pop("fraction", None)
    item["references"] = ["Edge-7"]
    item["parameters"]["method"] = "Vertex"
    item["parameters"]["vertices"] = ["Vertex-3"]

    decoded = project_from_dict(encoded)
    migrated = decoded.parts[0].geometry[-1]
    assert decoded.schema_version == 18
    assert migrated.target.items[0].operand.dimension == 1
    assert migrated.target.items[0].operand.tag == 7
    assert migrated.split_target.items[0].operand.dimension == 0
    assert migrated.split_target.items[0].operand.tag == 3


def test_schema_17_geometry_parameter_bags_migrate_to_explicit_fields(project_factory):
    from opencae.model.geometry import ImportedStepFeature, PartitionFaceFeature

    data = project_factory(include_constraints=False)
    part = data["part"]
    part.geometry.extend([
        ImportedStepFeature(name="SOURCE", source_file="model.step"),
        PartitionFaceFeature(name="FACE_SPLIT", points=((0, 0, 0), (1, 0, 0))),
    ])
    data["project"].rebuild_index()
    encoded = project_to_dict(data["project"])
    encoded["schema_version"] = 17
    source, face = encoded["parts"][0]["geometry"][-2:]
    source.pop("source_file", None); source["parameters"] = {"file": "legacy.step"}
    face.pop("points", None); face["parameters"] = {"points": {"__tuple__": [{"__tuple__": [0, 0, 0]}, {"__tuple__": [2, 0, 0]}]}}

    decoded = project_from_dict(encoded)
    assert decoded.schema_version == 18
    assert decoded.parts[0].geometry[-2].source_file == "legacy.step"
    assert decoded.parts[0].geometry[-1].points == ((0.0, 0.0, 0.0), (2.0, 0.0, 0.0))
