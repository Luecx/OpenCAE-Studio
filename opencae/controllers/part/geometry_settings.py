from copy import deepcopy

from opencae.ui.dialogs.geometry_settings import GeometrySettingsDialog

from ..dialog_runner import get_values


class PartGeometrySettings:
    def __init__(self, context):
        self.ctx = context

    def geometry_settings(self):
        part = self.ctx.active_part()
        if part is None:
            self.ctx.store.message.emit("Create or import a part first")
            return
        values = get_values(GeometrySettingsDialog(part.geometry_settings, self.ctx.parent))
        if not values:
            return
        candidate = deepcopy(part)
        for key, value in values.items():
            setattr(candidate.geometry_settings, key, value)
        if candidate.geometry and not self.ctx.validate_geometry(candidate, "Geometry settings failed"):
            return
        self.ctx.replace_part(candidate, "Updated geometry settings")
