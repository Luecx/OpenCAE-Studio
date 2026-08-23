from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator

from ...core import SolverWritable, register_model_type
from ..fem import Node


@register_model_type("node_table")
@dataclass
class NodeTable(SolverWritable):
    """Compact persisted node storage with an object-oriented public view."""

    ids: list[int] = field(default_factory=list)
    coordinates: list[tuple[float, float, float]] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.ids)

    def __iter__(self) -> Iterator[Node]:
        self._validate()
        return (
            Node(node_id, coords)
            for node_id, coords in zip(self.ids, self.coordinates, strict=True)
        )

    def _validate(self) -> None:
        if len(self.ids) != len(self.coordinates):
            raise ValueError("Node ids and coordinate arrays have different lengths")
        if len(set(self.ids)) != len(self.ids):
            raise ValueError("Mesh contains duplicate node ids")

    def next_id(self) -> int:
        return max(self.ids, default=0) + 1

    def get(self, node_id: int) -> Node:
        try:
            index = self.ids.index(int(node_id))
        except ValueError as exc:
            raise KeyError(f"Node {node_id} does not exist") from exc
        return Node(self.ids[index], self.coordinates[index])

    def add(
        self,
        value: Node | tuple[float, float, float],
        node_id: int | None = None,
    ) -> Node:
        node = (
            value
            if isinstance(value, Node)
            else Node(node_id or self.next_id(), tuple(value))
        )
        if node_id is not None and isinstance(value, Node) and node.id != int(node_id):
            raise ValueError("node_id does not match Node.id")
        if node.id in self.ids:
            raise ValueError(f"Node id {node.id} already exists")
        self.ids.append(node.id)
        self.coordinates.append(node.coordinates)
        return node

    def extend(self, values: Iterable[Node]) -> tuple[Node, ...]:
        added = []
        for value in values:
            added.append(self.add(value))
        return tuple(added)

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
