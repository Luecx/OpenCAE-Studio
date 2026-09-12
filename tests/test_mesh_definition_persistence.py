"""Regression coverage for canonical mesh element-definition persistence."""

from dataclasses import fields

import pytest

from opencae.model.core import EntityRef, decode_model, encode_model
from opencae.model.entities.mesh import ElementBlock, FiniteElementMesh, MeshState
from opencae.persistence.project_codec import (
    MINIMUM_SCHEMA_VERSION,
    project_from_dict,
    project_to_dict,
)


def test_mesh_definition_serializes_once_and_round_trips(project_factory):
    """FiniteElementMesh owns definitions while blocks persist references only."""
    project = project_factory(include_constraints=False)["project"]
    mesh = project.parts[0].mesh
    definition = mesh.element_definitions[0]

    assert mesh.element_blocks[0].definition is definition

    encoded = project_to_dict(project)
    persisted = encoded["project"]["parts"][0]["mesh"]
    finite_elements = persisted["finite_elements"]
    block = finite_elements["element_blocks"][0]

    assert set(persisted) >= {
        "recipe",
        "finite_elements",
        "associations",
        "quality",
        "lifecycle",
    }
    assert "element_definitions" not in persisted
    assert len(finite_elements["element_definitions"]) == 1
    assert "definition" not in block
    assert block["definition_ref"]["entity_id"] == definition.id

    decoded = project_from_dict(encoded)
    loaded = decoded.parts[0].mesh
    assert loaded.element_blocks[0].definition is loaded.element_definitions[0]
    assert loaded.element_definitions[0].count == 1
    assert decoded.index.path[loaded.element_definitions[0].id].endswith(
        ".mesh.finite_elements.element_definitions[0]"
    )


def test_bound_element_block_runtime_links_are_not_traversed(project_factory):
    project = project_factory(include_constraints=False)["project"]
    mesh = project.parts[0].mesh
    block = mesh.element_blocks[0]

    assert block.definition is mesh.element_definitions[0]
    assert block._mesh is mesh
    project.rebuild_index(strict=True)
    definition = mesh.element_definitions[0]
    assert project.resolve(definition.id) is definition
    assert project.index.parent_id[definition.id] == project.parts[0].id


def test_element_block_codec_accepts_persisted_definition_ref():
    block = ElementBlock(
        definition_ref=EntityRef("entity_definition", "ElementDefinition"),
        ids=[7],
        connectivity=[(1, 2, 3, 4)],
    )
    encoded = encode_model(block)
    assert "definition" not in encoded
    assert encoded["definition_ref"]["entity_id"] == "entity_definition"
    decoded = decode_model(encoded)
    assert isinstance(decoded, ElementBlock)
    assert decoded.definition is None
    assert decoded.definition_ref.entity_id == "entity_definition"
    assert decoded.ids == [7]
    assert decoded.connectivity == [(1, 2, 3, 4)]


def test_project_schema_older_than_migration_floor_is_rejected(project_factory):
    encoded = project_to_dict(project_factory(include_constraints=False)["project"])
    encoded["schema_version"] = MINIMUM_SCHEMA_VERSION - 1
    with pytest.raises(ValueError, match="is not supported"):
        project_from_dict(encoded)


def test_mesh_definition_ownership_contract_is_unambiguous():
    mesh_fields = {item.name: item for item in fields(MeshState)}
    finite_fields = {item.name: item for item in fields(FiniteElementMesh)}
    block_fields = {item.name: item for item in fields(ElementBlock)}

    assert set(mesh_fields) == {
        "recipe",
        "finite_elements",
        "associations",
        "quality",
        "lifecycle",
    }
    assert "element_definitions" in finite_fields
    assert "element_blocks" in finite_fields
    assert "definition_ref" in block_fields
    assert "definition" in block_fields
    assert block_fields["definition"].metadata.get("serialize") is False
