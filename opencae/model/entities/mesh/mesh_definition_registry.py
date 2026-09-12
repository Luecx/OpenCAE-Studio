"""Maintains canonical ElementDefinition ownership for compact mesh blocks."""

from __future__ import annotations

from ..elements.base import ElementDefinition
from .element_block import ElementBlock


def definition_for(mesh, reference) -> ElementDefinition | None:
    """Return the canonical definition represented by an object or identity."""
    if isinstance(reference, ElementDefinition):
        return next(
            (item for item in mesh.element_definitions if item is reference or item.id == reference.id),
            None,
        )
    entity_id = str(getattr(reference, "entity_id", reference) or "")
    return next(
        (definition for definition in mesh.element_definitions if definition.id == entity_id),
        None,
    )


def replace_element_blocks(mesh, blocks: list[ElementBlock]) -> None:
    """Replace blocks and rebuild one canonical definition collection."""
    source_definitions = []
    for block in blocks:
        definition = definition_for(mesh, block.definition) or block.definition
        if not isinstance(definition, ElementDefinition):
            raise ValueError("Cannot adopt an ElementBlock without a definition object")
        source_definitions.append(definition)

    canonical: list[ElementDefinition] = []
    by_key: dict[tuple, ElementDefinition] = {}
    for definition in source_definitions:
        key = definition_key(definition)
        if key not in by_key:
            by_key[key] = definition
            canonical.append(definition)

    _set_definitions(mesh, canonical)
    _set_blocks(mesh, list(blocks))
    for block, source in zip(mesh.element_blocks, source_definitions, strict=True):
        _bind_block(mesh, block, by_key[definition_key(source)])
    refresh_definition_counts(mesh)


def bind_element_blocks(mesh, register_missing: bool = True) -> None:
    """Bind blocks to canonical direct ElementDefinition objects."""
    blocks = list(getattr(mesh, "element_blocks", ()))
    definitions = list(getattr(mesh, "element_definitions", ()))
    by_id = {definition.id: definition for definition in definitions}
    bindings: list[tuple[ElementBlock, ElementDefinition]] = []

    for block in blocks:
        runtime_definition = block.definition
        identity = getattr(runtime_definition, "entity_id", None) or getattr(runtime_definition, "id", None)
        definition = by_id.get(str(identity or ""))
        if definition is None and isinstance(runtime_definition, ElementDefinition):
            if not register_missing:
                raise ValueError("ElementBlock definition is not owned by its mesh")
            equivalent = next(
                (item for item in definitions if definition_key(item) == definition_key(runtime_definition)),
                None,
            )
            definition = equivalent or runtime_definition
            if equivalent is None:
                definitions.append(definition)
                by_id[definition.id] = definition
        if definition is None:
            raise ValueError("ElementBlock references an unknown ElementDefinition")
        bindings.append((block, definition))

    _set_definitions(mesh, definitions)
    for block, definition in bindings:
        _bind_block(mesh, block, definition)
    refresh_definition_counts(mesh)


def refresh_definition_counts(mesh) -> None:
    counts = {definition.id: 0 for definition in mesh.element_definitions}
    for block in mesh.element_blocks:
        if block.definition is None:
            continue
        counts[block.definition.id] = counts.get(block.definition.id, 0) + len(block)
    for definition in mesh.element_definitions:
        definition.count = counts.get(definition.id, 0)


def definition_key(definition: ElementDefinition) -> tuple:
    return (
        type(definition),
        definition.name,
        definition.category,
        definition.topology,
        definition.order,
        definition.formulation,
        int(definition.gmsh_type),
    )


def _set_definitions(mesh, values) -> None:
    finite_elements = getattr(mesh, "finite_elements", None)
    if finite_elements is not None:
        finite_elements.element_definitions = list(values)
    else:
        object.__setattr__(mesh, "element_definitions", list(values))


def _set_blocks(mesh, values) -> None:
    finite_elements = getattr(mesh, "finite_elements", None)
    if finite_elements is not None:
        finite_elements.element_blocks = list(values)
    else:
        object.__setattr__(mesh, "element_blocks", list(values))


def _bind_block(mesh, block: ElementBlock, definition: ElementDefinition) -> None:
    block.definition = definition
    block.bind_mesh(mesh)
