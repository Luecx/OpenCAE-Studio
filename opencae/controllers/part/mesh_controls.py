from opencae.model.mesh import create_mesh_control
from opencae.ui.dialogs.mesh_control import MeshControlDialog
from opencae.ui.dialogs.mesh_settings import MeshSettingsDialog

from ..dialog_runner import get_values


class PartMeshControls:
    def __init__(self, context):
        self.ctx = context

    def mesh_control(self):
        part = self.ctx.active_part()
        if not self.ctx.require_geometry(part):
            return
        values = get_values(MeshControlDialog(self.ctx.selected_labels(), parent=self.ctx.parent))
        if not values:
            return
        technique = values["technique"]
        control = create_mesh_control(
            technique,
            name=values["name"], scope=values["scope"], topology=values["topology"],
            targets=self.ctx.split_labels(values["targets"]),
        )
        self.ctx.store.mutate(f"Created {control.name}", lambda project: part.mesh.controls.append(control))
        part.mesh.status = "Outdated"
        self.ctx.service.invalidate(part.id, mesh_only=True)

    def mesh_settings(self):
        part = self.ctx.active_part()
        if part is None:
            self.ctx.store.message.emit("Create or import a part first")
            return
        values = get_values(MeshSettingsDialog(part.mesh.settings, self.ctx.parent))
        if not values:
            return
        def update(_project):
            for key, value in values.items():
                setattr(part.mesh.settings, key, value)
            part.mesh.status = "Outdated"
        self.ctx.store.mutate("Updated Gmsh mesh settings", update)
        self.ctx.service.invalidate(part.id, mesh_only=True)

    def edit_mesh_control(self, control):
        part = self.ctx.active_part()
        values = get_values(MeshControlDialog(control=control, parent=self.ctx.parent)) if part else None
        if not values:
            return
        def update(_project):
            for key in ("name", "scope", "topology", "technique"):
                setattr(control, key, values[key])
            control.targets = self.ctx.split_labels(values["targets"])
            part.mesh.status = "Outdated"
        self.ctx.store.mutate(f"Edited {control.name}", update)
        self.ctx.service.invalidate(part.id, mesh_only=True)
