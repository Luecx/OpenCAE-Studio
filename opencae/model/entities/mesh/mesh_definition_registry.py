"""Maintains canonical ElementDefinition ownership for compact mesh blocks."""

from __future__ import annotations

from ...core import EntityRef
from ..elements.base import ElementDefinition
from .element_block import ElementBlock


def definition_for(
    mesh,
    reference: EntityRef | str | None,
) -> ElementDefinition | None:
    """Resolve one block definition reference within a MeshState."""
    entity_id = (
        reference.entity_id
        if isinstance(reference, EntityRef)
        else str(reference or "")
    )
    return next(
        (
            definition
            for definition in mesh.element_definitions
            if definition.id == entity_id
        ),
        None,
    )


def replace_element_blocks(mesh, blocks: list[ElementBlock]) -> None:
    """Replace blocks and rebuild one canonical definition collection."""
    source_definitions = []
    for block in blocks:
        definition = block.definition
        if definition is None:
            definition = definition_for(mesh, block.definition_ref)
        if definition is None:
            raise ValueError(
                "Cannot adopt an ElementBlock without a bound definition"
            )
        source_definitions.append(definition)

    canonical: list[ElementDefinition] = []
    by_key: dict[tuple, ElementDefinition] = {}
    for definition in source_definitions:
        key = definition_key(definition)
        if key not in by_key:
            by_key[key] = definition
            canonical.append(definition)

    object.__setattr__(mesh, "element_definitions", canonical)
    object.__setattr__(mesh, "element_blocks", list(blocks))
    for block, source in zip(
        mesh.element_blocks,
        source_definitions,
        strict=True,
    ):
        definition = by_key[definition_key(source)]
        _bind_block(mesh, block, definition)
    refresh_definition_counts(mesh)


def bind_element_blocks(mesh, register_missing: bool = True) -> None:
    """Bind current blocks and optionally register runtime definitions."""
    if "element_blocks" not in mesh.__dict__:
        return
    definitions = list(getattr(mesh, "element_definitions", ()))
    by_id = {definition.id: definition for definition in definitions}
    bindings: list[tuple[ElementBlock, ElementDefinition]] = []

    for block in mesh.element_blocks:
        definition = by_id.get(block.definition_ref.entity_id)
        runtime_definition = block.definition
        if definition is None and runtime_definition is not None:
            if not register_missing:
                raise ValueError(
                    "ElementBlock definition is not owned by MeshState"
                )
            equivalent = next(
                (
                    item
                    for item in definitions
                    if definition_key(item)
                    == definition_key(runtime_definition)
                ),
                None,
            )
            definition = equivalent or runtime_definition
            if equivalent is None:
                definitions.append(definition)
                by_id[definition.id] = definition

        if definition is None:
            raise ValueError(
                "ElementBlock references unknown definition "
                f"'{block.definition_ref.entity_id}'"
            )
        bindings.append((block, definition))

    object.__setattr__(mesh, "element_definitions", definitions)
    for block, definition in bindings:
        _bind_block(mesh, block, definition)
    refresh_definition_counts(mesh)


def refresh_definition_counts(mesh) -> None:
    """Synchronize definition summary counts from compact block membership."""
    counts = {definition.id: 0 for definition in mesh.element_definitions}
    for block in mesh.element_blocks:
        key = block.definition_ref.entity_id
        counts[key] = counts.get(key, 0) + len(block)
    for definition in mesh.element_definitions:
        definition.count = counts.get(definition.id, 0)


def definition_key(definition: ElementDefinition) -> tuple:
    """Return identity-independent solver metadata used to share definitions."""
    return (
        type(definition),
        definition.name,
        definition.category,
        definition.topology,
        definition.order,
        definition.formulation,
        int(definition.gmsh_type),
    )


def _bind_block(
    mesh,
    block: ElementBlock,
    definition: ElementDefinition,
) -> None:
    """Bind one block to a canonical definition already owned by the mesh."""
    block.definition_ref = EntityRef.of(definition, "ElementDefinition")
    block.definition = definition
    block.bind_mesh(mesh)
