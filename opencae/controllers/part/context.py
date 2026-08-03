from __future__ import annotations

from copy import deepcopy

from PyQt6.QtWidgets import QMessageBox

from opencae.geometry import GeometryService
from opencae.geometry.errors import GeometryError
from opencae.model.geometry import GeometryFeature
from opencae.model.selection import ViewportSelection

from ..busy import busy_cursor


class PartContext:
    def __init__(self, store, parent):
        self.store = store
        self.parent = parent
        self.service = GeometryService()

    def active_part(self):
        return self.store.active_part()

    def replace_part(self, candidate, description):
        part_id = candidate.id
        self.store.replace_entity(description, self.store.project.id, "parts", candidate)
        self.store.set_active_part(part_id)
        self.store.invalidate_scene(description)

    def validate_geometry(self, candidate, title):
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
            hit.label for hit in selection.hits
            if (expected_dim is None or hit.dimension == expected_dim) and hit.label
        )

    def selected_points(self):
        selection = self.store.selection
        if not isinstance(selection, ViewportSelection):
            return ()
        return tuple(hit.world_position for hit in selection.hits if hit.world_position is not None)

    @staticmethod
    def split_labels(text):
        return [value.strip() for value in str(text).split(",") if value.strip()]

    def feature_copy(self, feature: GeometryFeature):
        part = self.active_part()
        candidate = deepcopy(part) if part else None
        target = next((item for item in candidate.geometry if item.id == feature.id), None) if candidate else None
        return candidate, target

    def error(self, title, error):
        QMessageBox.critical(self.parent, title, str(error))
        self.store.message.emit(f"{title}: {error}")
