"""Stores compact element connectivity linked to one canonical definition."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...core import EntityRef, SolverWritable, as_entity_ref, register_model_type
from ..elements.base import ElementDefinition
from ..fem import Element


@register_model_type("element_block")
@dataclass(init=False)
class ElementBlock(SolverWritable):
    """Compact element storage referencing a MeshState-owned definition."""

    definition_ref: EntityRef
    ids: list[int] = field(default_factory=list)
    connectivity: list[tuple[int, ...]] = field(default_factory=list)

    def __init__(
        self,
        definition: ElementDefinition | EntityRef | None = None,
        ids: list[int] | tuple[int, ...] | None = None,
        connectivity: list[tuple[int, ...]] | tuple[tuple[int, ...], ...] | None = None,
        *,
        definition_ref: EntityRef | None = None,
    ) -> None:
        """Create a block from a public definition object or a persisted reference."""
        if definition is not None and definition_ref is not None:
            raise TypeError("Pass either definition or definition_ref, not both")
        source = definition if definition is not None else definition_ref
        if source is None:
            raise TypeError("ElementBlock requires an element definition")

        self.definition_ref = as_entity_ref(source, "ElementDefinition")
        self.ids = [int(value) for value in (ids or ())]
        self.connectivity = [
            tuple(int(node_id) for node_id in row)
            for row in (connectivity or ())
        ]
        if len(self.ids) != len(self.connectivity):
            raise ValueError("ElementBlock ids and connectivity must have equal length")

        # Runtime object access remains object-oriented. Only definition_ref is
        # persisted, so the same ElementDefinition is never serialized twice.
        self._definition = (
            source if isinstance(source, ElementDefinition) else None
        )
        self._mesh = None

    @property
    def definition(self) -> ElementDefinition:
        """Return the canonical definition object referenced by this block."""
        mesh = getattr(self, "_mesh", None)
        if mesh is not None:
            definition = mesh.definition_for(self.definition_ref)
            if definition is not None:
                return definition

        definition = getattr(self, "_definition", None)
        if definition is not None:
            return definition
        raise RuntimeError(
            f"Element definition '{self.definition_ref.entity_id}' is not bound"
        )

    def bind_mesh(self, mesh) -> None:
        """Bind this block to its owning MeshState and validate its reference."""
        definition = mesh.definition_for(self.definition_ref)
        if definition is None:
            raise ValueError(
                "ElementBlock references an element definition that is not "
                "owned by its MeshState"
            )
        self._mesh = mesh
        self._definition = definition

    def __len__(self) -> int:
        return len(self.ids)

    def add(self, element: Element) -> None:
        """Append one element while preserving definition compatibility."""
        if not isinstance(element, Element):
            raise TypeError("ElementBlock.add expects an Element object")
        if not isinstance(self.definition, element.definition_type):
            raise TypeError(
                f"{type(element).__name__} is incompatible with "
                f"{type(self.definition).__name__}"
            )
        if element.id in self.ids:
            raise ValueError(f"Element id {element.id} already exists in block")
        self.ids.append(element.id)
        self.connectivity.append(element.connectivity)

    def write_abaqus(self, writer, context) -> None:
        """Element blocks are emitted by solver-specific mesh exporters."""
        return None

    def write_femaster(self, writer, context) -> None:
        """Element blocks are emitted by solver-specific mesh exporters."""
        return None
