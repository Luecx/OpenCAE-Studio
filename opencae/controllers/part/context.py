"""Shared controller context for Part editing, geometry validation, and selection."""

from __future__ import annotations

from copy import copy, deepcopy

from PyQt6.QtWidgets import QMessageBox

from opencae.geometry import GeometryService
from opencae.geometry.errors import GeometryError
from opencae.model.geometry import GeometryFeature
from opencae.model.mesh import MeshState
from opencae.model.selection import ViewportSelection
from opencae.store.commands import CompositeCommand, UpdateFieldCommand
from opencae.store.owned_field_swap import OwnedFieldSwapCommand

from ..busy import busy_cursor


class PartContext:
    """Provide Part-controller services without owning persistent model state."""

    def __init__(self, store, parent, units=None):
        self.store = store
        self.parent = parent
        self.units = units
        self.app_settings = getattr(getattr(parent, "context", None), "settings", None)
        self.service = GeometryService()

    def active_part(self):
        return self.store.active_part()

    def replace_mesh(self, part_id, mesh, description):
        """Install a detached MeshState by zero-copy ownership transfer.

        The old mesh is moved into the undo entry and the new mesh is moved into
        the live Part. Undo/redo swap those two objects, so generated node and
        element payloads are never duplicated merely to support history.
        """
        self.store.execute(
            description,
            OwnedFieldSwapCommand(part_id, "mesh", mesh),
        )
        self.store.set_active_part(part_id)
        self.store.invalidate_scene(description)

    def geometry_candidate(self, part=None):
        """Create a geometry-edit candidate without copying generated FE payloads.

        Geometry validation only needs Part identity, geometry history/settings,
        region/datum context and lightweight mesh metadata. The generated node
        and element arrays may contain millions of numeric values, so a normal
        ``deepcopy(part)`` is inappropriate for interactive geometry edits.
        """
        source = part or self.active_part()
        if source is None:
            return None
        candidate = copy(source)
        # A shallow copy initially carries the live runtime owner. Detach it
        # before assigning copied fields so the candidate cannot invalidate the
        # live ProjectIndex while it is edited in a dialog.
        object.__setattr__(candidate, "_project", None)
        candidate.geometry_settings = deepcopy(source.geometry_settings)
        candidate.geometry = deepcopy(source.geometry)
        # Geometry flows only toggle persistent mesh status. Keep all large mesh
        # containers shared read-only while giving the candidate its own scalar
        # MeshState shell so status changes cannot touch the live Part.
        candidate.mesh = copy(source.mesh)
        return candidate

    def mesh_generation_candidate(self, part=None):
        """Create a worker-safe meshing candidate without the existing FE mesh.

        Gmsh needs geometry plus meshing configuration, not the generated node /
        connectivity arrays it is about to replace. Copy only the small settings,
        seeds, controls and definition metadata required to generate a new mesh.
        """
        source = part or self.active_part()
        if source is None:
            return None
        candidate = self.geometry_candidate(source)
        candidate.mesh = MeshState(
            settings=deepcopy(source.mesh.settings),
            seeds=deepcopy(source.mesh.seeds),
            element_controls=deepcopy(source.mesh.element_controls),
            element_definitions=deepcopy(source.mesh.element_definitions),
            status=source.mesh.status,
            revision=source.mesh.revision,
        )
        return candidate

    def commit_geometry_candidate(self, candidate, description):
        """Commit only fields changed by a geometry edit, never the Part mesh."""
        live = self.store.project.try_resolve(candidate.id)
        if live is None:
            self.store.message.emit("The edited part no longer exists")
            return False

        commands = []
        for field_name in ("name", "geometry_settings", "geometry"):
            before = getattr(live, field_name)
            after = getattr(candidate, field_name)
            if before != after:
                commands.append(UpdateFieldCommand(live.id, field_name, before, after))
        if live.mesh.status != candidate.mesh.status:
            commands.append(
                UpdateFieldCommand(
                    live.id,
                    "mesh.status",
                    live.mesh.status,
                    candidate.mesh.status,
                )
            )
        if not commands:
            return False

        command = (
            commands[0]
            if len(commands) == 1
            else CompositeCommand(tuple(commands))
        )
        self.store.execute(description, command)
        self.store.set_active_part(live.id)
        self.store.invalidate_scene(description)
        return True

    def validate_geometry(self, candidate, title):
        """Build a detached candidate and surface geometry errors to the user."""
        try:
            with busy_cursor():
                self.service.build_geometry(candidate, force=True)
            return True
        except GeometryError as exc:
            self.error(title, exc)
            return False

    def require_geometry(self, part):
        if part is None or not part.geometry:
            self.store.message.emit("Import STEP, IGES or BREP geometry first")
            return False
        return True

    def selected_labels(self, expected_dim=None):
        selection = self.store.selection
        if not isinstance(selection, ViewportSelection):
            return ()
        return tuple(
            hit.label
            for hit in selection.hits
            if (expected_dim is None or hit.dimension == expected_dim) and hit.label
        )

    def selected_points(self):
        selection = self.store.selection
        if not isinstance(selection, ViewportSelection):
            return ()
        return tuple(
            hit.world_position
            for hit in selection.hits
            if hit.world_position is not None
        )

    @staticmethod
    def split_labels(text):
        return [value.strip() for value in str(text).split(",") if value.strip()]

    def feature_copy(self, feature: GeometryFeature):
        """Return a detached geometry candidate and its copied feature by ID."""
        candidate = self.geometry_candidate()
        target = (
            next((item for item in candidate.geometry if item.id == feature.id), None)
            if candidate
            else None
        )
        return candidate, target

    def error(self, title, error):
        QMessageBox.critical(self.parent, title, str(error))
        self.store.message.emit(f"{title}: {error}")
