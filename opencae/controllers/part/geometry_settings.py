"""Owns interactive geometry-settings edits for the active Part."""

from opencae.ui.dialogs.geometry_settings import GeometrySettingsDialog

from ..dialog_runner import get_values


class PartGeometrySettings:
    """Validate and commit geometry settings without cloning generated meshes."""

    def __init__(self, context):
        self.ctx = context

    def geometry_settings(self):
        """Edit geometry settings using a detached geometry-only candidate."""
        part = self.ctx.active_part()
        if part is None:
            self.ctx.store.message.emit("Create or import a part first")
            return
        values = get_values(
            GeometrySettingsDialog(part.geometry_settings, self.ctx.parent)
        )
        if not values:
            return

        candidate = self.ctx.geometry_candidate(part)
        for key, value in values.items():
            setattr(candidate.geometry_settings, key, value)
        candidate.mesh.status = "Outdated"
        if candidate.geometry and not self.ctx.validate_geometry(
            candidate,
            "Geometry settings failed",
        ):
            return
        self.ctx.commit_geometry_candidate(candidate, "Updated geometry settings")
