"""Stores compact element payload with direct definition/object relationships."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ...core import SolverWritable, register_model_type
from ..elements.base import ElementDefinition
from ..fem import Element, MeshEntityOrigin, element_class_for_definition

if TYPE_CHECKING:
    from .mesh_state import MeshState


@register_model_type("element_block")
@dataclass
class ElementBlock(SolverWritable):
    """Compact element storage exposing identity-stable Element objects."""

    definition: ElementDefinition | None = field(
        default=None,
        metadata={"reference_type": "ElementDefinition"},
    )
    ids: list[int] = field(
        default_factory=list,
        metadata={"project_index": False},
    )
    connectivity: list[tuple[int, ...]] = field(
        default_factory=list,
        metadata={"project_index": False},
    )
    origins: list[MeshEntityOrigin | str] = field(
        default_factory=list,
        metadata={"project_index": False},
    )
    _mesh: MeshState | None = field(
        init=False,
        default=None,
        repr=False,
        compare=False,
        metadata={"serialize": False},
    )
    _objects: dict[int, Element] = field(
        init=False,
        default_factory=dict,
        repr=False,
        compare=False,
        metadata={"serialize": False, "project_index": False},
    )

    def __post_init__(self) -> None:
        self.ids = [int(value) for value in self.ids]
        self.connectivity = [
            tuple(int(node_id) for node_id in row)
            for row in self.connectivity
        ]
        if not self.origins and self.ids:
            self.origins = [MeshEntityOrigin.GENERATED] * len(self.ids)
        else:
            self.origins = [MeshEntityOrigin.coerce(value) for value in self.origins]
        self._objects = {}
        if len(self.ids) != len(self.connectivity):
            raise ValueError("ElementBlock ids and connectivity must have equal length")
        if len(self.ids) != len(self.origins):
            raise ValueError("ElementBlock ids and origins must have equal length")

    def bind_mesh(self, mesh) -> None:
        """Bind compact rows to the owning mesh and canonical definition object."""
        definition = mesh.definition_for(self.definition)
        if definition is None:
            raise ValueError(
                "ElementBlock definition is not owned by its MeshState"
            )
        self._mesh = mesh
        self.definition = definition
        # Existing references remain valid. Re-synchronize them lazily through
        # get() rather than replacing them when a block is rebound.

    def __len__(self) -> int:
        return len(self.ids)

    def get(self, element_id: int) -> Element:
        """Return the one canonical Element object for ``element_id``."""
        if self._mesh is None or self.definition is None:
            raise RuntimeError("ElementBlock must be bound before reading elements")
        index = self.position(element_id)
        identity = self.ids[index]
        element_type = element_class_for_definition(self.definition)
        nodes = tuple(
            self._mesh.node(node_id) for node_id in self.connectivity[index]
        )
        element = self._objects.get(identity)
        if element is None or not isinstance(element, element_type):
            element = element_type(identity, nodes, self.origins[index])
            self._objects[identity] = element
        else:
            object.__setattr__(element, "nodes", nodes)
            object.__setattr__(element, "origin", self.origins[index])
        return element

    def add(self, element: Element) -> None:
        if not isinstance(element, Element):
            raise TypeError("ElementBlock.add expects an Element object")
        if self.definition is None:
            raise RuntimeError("ElementBlock has no bound ElementDefinition object")
        if not isinstance(self.definition, element.definition_type):
            raise TypeError(
                f"{type(element).__name__} is incompatible with "
                f"{type(self.definition).__name__}"
            )
        if element.id in self.ids:
            raise ValueError(f"Element id {element.id} already exists in block")
        self.ids.append(element.id)
        self.connectivity.append(element.connectivity)
        self.origins.append(element.origin)
        self._objects[element.id] = element

    def position(self, element_id: int) -> int:
        try:
            return self.ids.index(int(element_id))
        except ValueError as exc:
            raise KeyError(f"Element {element_id} does not exist") from exc

    def remove(self, element_id: int) -> tuple[tuple[int, ...], MeshEntityOrigin]:
        index = self.position(element_id)
        identity = self.ids[index]
        connectivity = self.connectivity.pop(index)
        origin = self.origins.pop(index)
        self.ids.pop(index)
        self._objects.pop(identity, None)
        return connectivity, origin

    def replace(self, element: Element) -> None:
        if self.definition is None or not isinstance(
            self.definition,
            element.definition_type,
        ):
            raise TypeError("Replacement element is incompatible with this block")
        index = self.position(element.id)
        self.connectivity[index] = element.connectivity
        self.origins[index] = element.origin
        current = self._objects.get(element.id)
        if current is None:
            self._objects[element.id] = element
        elif current is not element:
            object.__setattr__(current, "nodes", tuple(element.nodes))
            object.__setattr__(current, "origin", element.origin)

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
