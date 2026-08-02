from __future__ import annotations

from dataclasses import dataclass, field

from .snapshots import GeometrySnapshot, MeshSnapshot


@dataclass
class GeometryCache:
    geometries: dict[str, GeometrySnapshot] = field(default_factory=dict)
    meshes: dict[str, MeshSnapshot] = field(default_factory=dict)

    def geometry(self, part_id: str) -> GeometrySnapshot | None:
        return self.geometries.get(part_id)

    def mesh(self, part_id: str) -> MeshSnapshot | None:
        return self.meshes.get(part_id)

    def set_geometry(self, snapshot: GeometrySnapshot) -> None:
        self.geometries[snapshot.part_id] = snapshot

    def set_mesh(self, snapshot: MeshSnapshot) -> None:
        self.meshes[snapshot.part_id] = snapshot

    def invalidate(self, part_id: str, mesh_only: bool = False) -> None:
        self.meshes.pop(part_id, None)
        if not mesh_only:
            self.geometries.pop(part_id, None)

    def clear(self) -> None:
        self.geometries.clear()
        self.meshes.clear()


CACHE = GeometryCache()
