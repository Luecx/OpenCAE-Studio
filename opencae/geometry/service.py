"""Owns geometry/mesh generation sessions and their runtime cache lifecycle."""

from __future__ import annotations

from .cache import CACHE
from .element_controls_apply import requires_second_order
from .extract_geometry import extract_geometry
from .extract_mesh import extract_mesh
from .fingerprint import part_fingerprint
from .gmsh_session import gmsh_model
from .history import rebuild_occ
from .mesh_options import apply_default_seed, apply_general_options
from .seed_validation import edge_seed_mismatches
from .seeding import apply_edge_seeds


class GeometryService:
    """Build geometry and mesh snapshots without owning persistent model state."""

    def build_geometry(self, part, force: bool = False):
        """Build or reuse the current geometry snapshot for one Part."""
        fingerprint = part_fingerprint(part)
        cached = CACHE.geometry(part.id)
        if cached and cached.fingerprint == fingerprint and not force:
            return cached
        with gmsh_model(part.name) as gmsh:
            rebuild_occ(gmsh, part)
            snapshot = extract_geometry(
                gmsh,
                part.id,
                fingerprint,
                part.geometry_settings.display_size_factor,
            )
        CACHE.set_geometry(snapshot)
        CACHE.invalidate(part.id, mesh_only=True)
        return snapshot

    def generate_mesh(self, part):
        """Generate and cache one mesh snapshot for the supplied Part state."""
        fingerprint = part_fingerprint(part, include_mesh=True)
        with gmsh_model(part.name) as gmsh:
            rebuild_occ(gmsh, part)
            apply_general_options(gmsh, part)
            apply_default_seed(gmsh, part)
            apply_edge_seeds(gmsh, part)
            dimension = self._mesh_dimension(gmsh)
            gmsh.model.mesh.generate(dimension)
            if requires_second_order(part):
                gmsh.model.mesh.setOrder(2)
            if part.mesh.settings.optimize:
                gmsh.model.mesh.optimize("Netgen")
            if (
                part.mesh.settings.high_order_optimize
                and requires_second_order(part)
            ):
                gmsh.model.mesh.optimize("HighOrder")
            snapshot = extract_mesh(
                gmsh,
                part.id,
                dimension,
                fingerprint,
            )
            snapshot.seed_mismatches = edge_seed_mismatches(gmsh, part)
        CACHE.set_mesh(snapshot)
        return snapshot

    @staticmethod
    def _mesh_dimension(gmsh):
        """Return the highest geometric dimension available in the Gmsh model."""
        if gmsh.model.getEntities(3):
            return 3
        if gmsh.model.getEntities(2):
            return 2
        if gmsh.model.getEntities(1):
            return 1
        return 0

    def invalidate(self, part_id: str, mesh_only: bool = False):
        """Invalidate cached geometry or mesh state for one Part."""
        CACHE.invalidate(part_id, mesh_only)

    def clear(self):
        """Clear all cached geometry and mesh snapshots."""
        CACHE.clear()
