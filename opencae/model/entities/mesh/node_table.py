"""Stores compact mesh-node payload while exposing canonical Node objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator

from ...core import SolverWritable, register_model_type
from ..fem import MeshEntityOrigin, Node


@register_model_type("node_table")
@dataclass
class NodeTable(SolverWritable):
    """Compact persisted node storage with identity-stable runtime objects."""

    ids: list[int] = field(
        default_factory=list,
        metadata={"project_index": False},
    )
    coordinates: list[tuple[float, float, float]] = field(
        default_factory=list,
        metadata={"project_index": False},
    )
    origins: list[MeshEntityOrigin | str] = field(
        default_factory=list,
        metadata={"project_index": False},
    )
    _objects: dict[int, Node] = field(
        init=False,
        default_factory=dict,
        repr=False,
        compare=False,
        metadata={"serialize": False, "project_index": False},
    )

    def __post_init__(self) -> None:
        self.ids = [int(value) for value in self.ids]
        self.coordinates = [
            tuple(float(item) for item in row) for row in self.coordinates
        ]
        if not self.origins and self.ids:
            self.origins = [MeshEntityOrigin.GENERATED] * len(self.ids)
        else:
            self.origins = [MeshEntityOrigin.coerce(value) for value in self.origins]
        self._objects = {}
        self._validate()

    def __len__(self) -> int:
        return len(self.ids)

    def __iter__(self) -> Iterator[Node]:
        self._validate()
        return (self.get(node_id) for node_id in self.ids)

    def _validate(self) -> None:
        if len(self.ids) != len(self.coordinates):
            raise ValueError("Node ids and coordinate arrays have different lengths")
        if len(self.ids) != len(self.origins):
            raise ValueError("Node ids and origin arrays have different lengths")
        if len(set(self.ids)) != len(self.ids):
            raise ValueError("Mesh contains duplicate node ids")

    def next_id(self) -> int:
        return max(self.ids, default=0) + 1

    def get(self, node_id: int) -> Node:
        """Return the one canonical Node object for ``node_id``."""
        index = self._position(node_id)
        identity = self.ids[index]
        node = self._objects.get(identity)
        if node is None:
            node = Node(identity, self.coordinates[index], self.origins[index])
            self._objects[identity] = node
        else:
            # Compact arrays remain persistence/solver storage. Keep an already
            # referenced Node object synchronized in-place when rows are loaded
            # or restored by undo/redo.
            object.__setattr__(node, "coordinates", self.coordinates[index])
            object.__setattr__(node, "origin", self.origins[index])
        return node

    def add(
        self,
        value: Node | tuple[float, float, float],
        node_id: int | None = None,
        origin: MeshEntityOrigin | str | None = None,
    ) -> Node:
        """Append one unique node and retain the supplied Node as canonical."""
        node = (
            value
            if isinstance(value, Node)
            else Node(
                node_id or self.next_id(),
                tuple(value),
                origin or MeshEntityOrigin.AUTHORED,
            )
        )
        if node_id is not None and isinstance(value, Node) and node.id != int(node_id):
            raise ValueError("node_id does not match Node.id")
        if node.id in self.ids:
            raise ValueError(f"Node id {node.id} already exists")
        final_origin = MeshEntityOrigin.coerce(origin) if origin is not None else node.origin
        if final_origin is not node.origin:
            object.__setattr__(node, "origin", final_origin)
        self.ids.append(node.id)
        self.coordinates.append(node.coordinates)
        self.origins.append(final_origin)
        self._objects[node.id] = node
        return node

    def update(
        self,
        node_id: int,
        coordinates: tuple[float, float, float],
        *,
        origin: MeshEntityOrigin | str = MeshEntityOrigin.AUTHORED,
    ) -> Node:
        """Mutate one canonical Node while retaining its stable object identity."""
        index = self._position(node_id)
        validated = Node(node_id, coordinates, origin)
        self.coordinates[index] = validated.coordinates
        self.origins[index] = validated.origin
        node = self.get(node_id)
        object.__setattr__(node, "coordinates", validated.coordinates)
        object.__setattr__(node, "origin", validated.origin)
        return node

    def remove(self, node_id: int) -> Node:
        """Remove and return the canonical Node object."""
        index = self._position(node_id)
        node = self.get(node_id)
        identity = self.ids[index]
        del self.ids[index]
        del self.coordinates[index]
        del self.origins[index]
        self._objects.pop(identity, None)
        return node

    def _position(self, node_id: int) -> int:
        try:
            return self.ids.index(int(node_id))
        except ValueError as exc:
            raise KeyError(f"Node {node_id} does not exist") from exc

    def extend(self, values: Iterable[Node]) -> tuple[Node, ...]:
        return tuple(self.add(value) for value in values)

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
