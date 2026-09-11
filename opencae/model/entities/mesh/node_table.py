"""Stores persisted mesh nodes without exposing numeric arrays to ProjectIndex."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator

from ...core import SolverWritable, register_model_type
from ..fem import MeshEntityOrigin, Node


@register_model_type("node_table")
@dataclass
class NodeTable(SolverWritable):
    """Compact persisted node storage with an object-oriented public view."""

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

    def __post_init__(self) -> None:
        """Normalize compact rows and infer provenance for legacy mesh data."""
        self.ids = [int(value) for value in self.ids]
        self.coordinates = [
            tuple(float(item) for item in row) for row in self.coordinates
        ]
        if not self.origins and self.ids:
            self.origins = [MeshEntityOrigin.GENERATED] * len(self.ids)
        else:
            self.origins = [
                MeshEntityOrigin.coerce(value) for value in self.origins
            ]
        self._validate()

    def __len__(self) -> int:
        return len(self.ids)

    def __iter__(self) -> Iterator[Node]:
        self._validate()
        return (
            Node(node_id, coords, origin)
            for node_id, coords, origin in zip(
                self.ids,
                self.coordinates,
                self.origins,
                strict=True,
            )
        )

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
        try:
            index = self.ids.index(int(node_id))
        except ValueError as exc:
            raise KeyError(f"Node {node_id} does not exist") from exc
        return Node(self.ids[index], self.coordinates[index], self.origins[index])

    def add(
        self,
        value: Node | tuple[float, float, float],
        node_id: int | None = None,
        origin: MeshEntityOrigin | str | None = None,
    ) -> Node:
        """Append one unique node and return its canonical value object."""
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
        self.ids.append(node.id)
        self.coordinates.append(node.coordinates)
        self.origins.append(
            MeshEntityOrigin.coerce(origin) if origin is not None else node.origin
        )
        return node

    def update(
        self,
        node_id: int,
        coordinates: tuple[float, float, float],
        *,
        origin: MeshEntityOrigin | str = MeshEntityOrigin.AUTHORED,
    ) -> Node:
        """Replace one node's coordinates without changing its stable ID."""
        index = self._position(node_id)
        node = Node(node_id, coordinates, origin)
        self.coordinates[index] = node.coordinates
        self.origins[index] = node.origin
        return node

    def remove(self, node_id: int) -> Node:
        """Remove and return one node after the owning mesh checks connectivity."""
        index = self._position(node_id)
        node = Node(
            self.ids[index],
            self.coordinates[index],
            self.origins[index],
        )
        del self.ids[index]
        del self.coordinates[index]
        del self.origins[index]
        return node

    def _position(self, node_id: int) -> int:
        """Return the compact row for a node or raise a stable lookup error."""
        try:
            return self.ids.index(int(node_id))
        except ValueError as exc:
            raise KeyError(f"Node {node_id} does not exist") from exc

    def extend(self, values: Iterable[Node]) -> tuple[Node, ...]:
        added = []
        for value in values:
            added.append(self.add(value))
        return tuple(added)

    def write_abaqus(self, writer, context) -> None:
        """Defer node output to solver-specific mesh exporters."""
        return None

    def write_femaster(self, writer, context) -> None:
        """Defer node output to solver-specific mesh exporters."""
        return None
