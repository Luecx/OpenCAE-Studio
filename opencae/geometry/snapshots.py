from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class SurfacePatch:
    tag: int
    points: np.ndarray
    faces: np.ndarray


@dataclass
class VertexPatch:
    tag: int
    point: np.ndarray


@dataclass
class EdgePatch:
    tag: int
    points: np.ndarray
    lines: np.ndarray


@dataclass
class GeometrySnapshot:
    part_id: str
    surfaces: list[SurfacePatch] = field(default_factory=list)
    edges: list[EdgePatch] = field(default_factory=list)
    vertices: list[VertexPatch] = field(default_factory=list)
    entities: dict[int, list[int]] = field(default_factory=dict)
    surface_to_cells: dict[int, list[int]] = field(default_factory=dict)
    bounds: tuple[float, float, float, float, float, float] | None = None
    fingerprint: str = ""

    @property
    def empty(self) -> bool:
        return not self.surfaces and not self.edges


@dataclass
class MeshBlock:
    gmsh_type: int
    name: str
    dimension: int
    order: int
    primary_nodes: int
    connectivity: np.ndarray
    element_tags: np.ndarray | None = None


@dataclass
class MeshSnapshot:
    part_id: str
    node_tags: np.ndarray
    points: np.ndarray
    blocks: list[MeshBlock]
    dimension: int
    fingerprint: str = ""
    qualities: np.ndarray | None = None
    entity_nodes: dict[str, list[int]] = field(default_factory=dict)
    entity_elements: dict[str, list[int]] = field(default_factory=dict)
    seed_mismatches: dict[str, tuple[int | None, int | None]] = field(default_factory=dict)

    @property
    def element_count(self) -> int:
        return sum(len(block.connectivity) for block in self.blocks)
