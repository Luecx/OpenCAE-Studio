"""Stores compact element connectivity linked to one canonical definition."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...core import EntityRef, SolverWritable, as_entity_ref, register_model_type
from ..elements.base import ElementDefinition
from ..fem import Element


@register_model_type("element_block")
@dataclass
class ElementBlock(SolverWritable):
    """Compact element storage referencing a MeshState-owned definition.

    ``definition`` is a non-serialized runtime alias so the public API remains
    object-oriented. ``definition_ref`` is the only persisted relationship.
    """

    definition: ElementDefinition | EntityRef | None = field(
        default=None,
        metadata={"serialize": False},
        repr=False,
        compare=False,
    )
    ids: list[int] = field(default_factory=list)
    connectivity: list[tuple[int, ...]] = field(default_factory=list)
    definition_ref: EntityRef | None = None
    _mesh: object | None = field(
        init=False,
        default=None,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        """Normalize public object input or a persisted reference."""
        if self.definition is not None and self.definition_ref is not None:
            runtime_ref = as_entity_ref(self.definition, "ElementDefinition")
            persisted_ref = as_entity_ref(
                self.definition_ref,
                "ElementDefinition",
            )
            if runtime_ref.entity_id != persisted_ref.entity_id:
                raise TypeError(
                    "Pass either definition or definition_ref, not conflicting both"
                )
            source = self.definition
        else:
            source = (
                self.definition
                if self.definition is not None
                else self.definition_ref
            )
        if source is None:
            raise TypeError("ElementBlock requires an element definition")

        self.definition_ref = as_entity_ref(source, "ElementDefinition")
        self.definition = (
            source if isinstance(source, ElementDefinition) else None
        )
        self.ids = [int(value) for value in self.ids]
        self.connectivity = [
            tuple(int(node_id) for node_id in row)
            for row in self.connectivity
        ]
        if len(self.ids) != len(self.connectivity):
            raise ValueError(
                "ElementBlock ids and connectivity must have equal length"
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
        self.definition = definition

    def __len__(self) -> int:
        """Return the number of compact elements in this block."""
        return len(self.ids)

    def add(self, element: Element) -> None:
        """Append one element while preserving definition compatibility."""
        if not isinstance(element, Element):
            raise TypeError("ElementBlock.add expects an Element object")
        if self.definition is None:
            raise RuntimeError(
                f"Element definition '{self.definition_ref.entity_id}' is not bound"
            )
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
