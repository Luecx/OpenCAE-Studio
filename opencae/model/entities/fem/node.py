"""Defines the authored finite-element Node value object."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class Node:
    """One finite-element node in the public authoring API."""

    id: int
    coordinates: tuple[float, float, float]

    def __post_init__(self) -> None:
        """Normalize the node and reject invalid identity/coordinates."""
        node_id = int(self.id)
        if node_id <= 0:
            raise ValueError("Node ids must be positive integers")

        coordinates = tuple(float(value) for value in self.coordinates)
        if len(coordinates) != 3:
            raise ValueError("A node requires exactly three coordinates")
        if not all(isfinite(value) for value in coordinates):
            raise ValueError("Node coordinates must be finite")

        object.__setattr__(self, "id", node_id)
        object.__setattr__(self, "coordinates", coordinates)

    @property
    def x(self) -> float:
        """Return the global x coordinate."""
        return self.coordinates[0]

    @property
    def y(self) -> float:
        """Return the global y coordinate."""
        return self.coordinates[1]

    @property
    def z(self) -> float:
        """Return the global z coordinate."""
        return self.coordinates[2]
