"""Cache expensive local-space PolyData preparation for CAD viewport rendering."""

from __future__ import annotations

import pyvista as pv

from opencae.geometry.meshability import oriented_faces


class GeometryRenderCache:
    """Keep cleaned/normals-ready topology meshes for the latest snapshot of each Part."""

    def __init__(self):
        """Create an empty one-entry-per-Part render-preparation cache."""
        self._entries: dict[str, tuple[object, dict, dict, dict]] = {}

    def prepared(self, snapshot):
        """Return local-space face, edge and vertex PolyData for one snapshot.

        GeometryService already caches tessellation snapshots. This second cache
        deliberately sits in the UI layer because ``clean`` and normal creation
        are rendering concerns. A changed geometry fingerprint replaces the old
        Part entry so stale VTK datasets cannot accumulate across rebuilds.
        """
        part_id = str(snapshot.part_id)
        token = snapshot.fingerprint or id(snapshot)
        cached = self._entries.get(part_id)
        if cached is not None and cached[0] == token:
            return cached[1], cached[2], cached[3]

        faces = {
            int(patch.tag): self._prepare_face(snapshot, patch)
            for patch in snapshot.surfaces
        }
        edges = {
            int(patch.tag): self._prepare_edge(patch)
            for patch in snapshot.edges
        }
        vertices = {
            int(patch.tag): pv.PolyData([patch.point])
            for patch in snapshot.vertices
        }
        self._entries[part_id] = (token, faces, edges, vertices)
        return faces, edges, vertices

    def invalidate(self, part_id: str) -> None:
        """Drop render-prepared datasets for one Part explicitly when required."""
        self._entries.pop(str(part_id), None)

    def clear(self) -> None:
        """Drop all prepared VTK datasets."""
        self._entries.clear()

    @staticmethod
    def _prepare_face(snapshot, patch):
        """Create one cleaned surface with stable cell/point normals."""
        mesh = pv.PolyData(patch.points, oriented_faces(snapshot, patch))
        try:
            mesh = mesh.clean(tolerance=1.0e-10, absolute=False)
        except (AttributeError, TypeError, ValueError, RuntimeError):
            pass
        try:
            mesh = mesh.compute_normals(
                cell_normals=True,
                point_normals=True,
                consistent_normals=True,
                auto_orient_normals=False,
                split_vertices=False,
                inplace=False,
            )
        except (TypeError, ValueError, RuntimeError):
            pass
        return mesh

    @staticmethod
    def _prepare_edge(patch):
        """Create one local-space CAD edge PolyData with its polyline connectivity."""
        mesh = pv.PolyData(patch.points)
        mesh.lines = patch.lines
        return mesh


GEOMETRY_RENDER_CACHE = GeometryRenderCache()
