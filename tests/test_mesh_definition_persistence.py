"""Regression coverage for canonical mesh element-definition persistence."""

from copy import deepcopy
from dataclasses import fields

from opencae.model.core import EntityRef, decode_model, encode_model
from opencae.model.entities.mesh import ElementBlock, MeshState
from opencae.persistence.project_codec import (
    CURRENT_SCHEMA_VERSION,
    project_from_dict,
    project_to_dict,
)


def test_mesh_definition_serializes_once_and_round_trips(project_factory):
    """Blocks persist refs while MeshState owns each ElementDefinition once."""
    project = project_factory(include_constraints=False)["project"]
    mesh = project.parts[0].mesh
    definition = mesh.element_definitions[0]

    assert mesh.element_blocks[0].definition is definition

    encoded = project_to_dict(project)
    persisted = encoded["parts"][0]["mesh"]
    block = persisted["element_blocks"][0]

    assert "elements" not in persisted
    assert len(persisted["element_definitions"]) == 1
    assert "definition" not in block
    assert block["definition_ref"]["entity_id"] == definition.id

    decoded = project_from_dict(encoded)
    loaded = decoded.parts[0].mesh
    assert loaded.element_blocks[0].definition is loaded.element_definitions[0]
    assert loaded.element_definitions[0].count == 1
    assert decoded.index.path[loaded.element_definitions[0].id].endswith(
        ".mesh.element_definitions[0]"
    )


def test_bound_element_block_runtime_links_are_not_traversed(project_factory):
    """Runtime definition and mesh aliases cannot form index traversal cycles."""
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
    """The generic model codec can construct ElementBlock from definition_ref."""
    block = ElementBlock(
        definition_ref=EntityRef(
            "entity_definition",
            "ElementDefinition",
        ),
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


def test_schema_20_duplicate_definition_migrates_before_indexing(project_factory):
    """Reproduce the duplicate-ID loader crash and verify schema-20 repair."""
    encoded = project_to_dict(
        project_factory(include_constraints=False)["project"]
    )
    encoded["schema_version"] = 20
    mesh = encoded["parts"][0]["mesh"]
    definitions = deepcopy(mesh.pop("element_definitions"))
    mesh["elements"] = deepcopy(definitions)

    for block in mesh["element_blocks"]:
        reference = block.pop("definition_ref")
        definition = deepcopy(definitions[0])
        assert definition["id"] == reference["entity_id"]
        block["definition"] = definition

    decoded = project_from_dict(encoded)
    loaded = decoded.parts[0].mesh

    assert decoded.schema_version == CURRENT_SCHEMA_VERSION
    assert len(loaded.element_definitions) == 1
    assert loaded.element_blocks[0].definition is loaded.element_definitions[0]


def test_schema_20_generated_aliases_match_definition_metadata(project_factory):
    """Schema-20 generated blocks with independent IDs collapse semantically."""
    encoded = project_to_dict(
        project_factory(include_constraints=False)["project"]
    )
    encoded["schema_version"] = 20
    mesh = encoded["parts"][0]["mesh"]
    definitions = deepcopy(mesh.pop("element_definitions"))
    mesh["elements"] = deepcopy(definitions)

    block = mesh["element_blocks"][0]
    block.pop("definition_ref")
    embedded = deepcopy(definitions[0])
    embedded["id"] = "entity_legacy_block_copy"
    block["definition"] = embedded

    decoded = project_from_dict(encoded)
    loaded = decoded.parts[0].mesh

    assert len(loaded.element_definitions) == 1
    assert loaded.element_blocks[0].definition is loaded.element_definitions[0]
    assert loaded.element_definitions[0].count == len(
        loaded.element_blocks[0]
    )


def test_mesh_definition_ownership_contract_is_unambiguous():
    """Protect one serialized owner plus a non-serialized runtime object alias."""
    mesh_fields = {item.name: item for item in fields(MeshState)}
    block_fields = {item.name: item for item in fields(ElementBlock)}

    assert "element_definitions" in mesh_fields
    assert "elements" not in mesh_fields
    assert "definition_ref" in block_fields
    assert "definition" in block_fields
    assert block_fields["definition"].metadata.get("serialize") is False
