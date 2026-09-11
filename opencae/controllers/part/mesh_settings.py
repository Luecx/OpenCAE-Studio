from __future__ import annotations

from copy import deepcopy

from opencae.model.entities.mesh import MeshValidity
from opencae.store.commands import CompositeCommand, UpdateFieldCommand
from opencae.ui.dialogs.mesh_settings import MeshSettingsDialog

from ..dialog_runner import get_values


class PartMeshSettings:
    """Edit persistent meshing recipe settings for the active Part."""

    def __init__(self, context):
        self.ctx = context

    def mesh_settings(self):
        part = self.ctx.active_part()
        if part is None:
            self.ctx.store.message.emit("Create or import a part first")
            return

        values = get_values(MeshSettingsDialog(part.mesh.settings, self.ctx.parent))
        if not values:
            return

        candidate = deepcopy(part.mesh.settings)
        for key, value in values.items():
            setattr(candidate, key, value)

        commands = [
            UpdateFieldCommand(
                part.id,
                "mesh.recipe.settings",
                part.mesh.settings,
                candidate,
            )
        ]
        if part.mesh.lifecycle.validity is not MeshValidity.OUTDATED:
            commands.append(
                UpdateFieldCommand(
                    part.id,
                    "mesh.lifecycle.validity",
                    part.mesh.lifecycle.validity,
                    MeshValidity.OUTDATED,
                )
            )

        self.ctx.store.execute(
            "Updated Gmsh mesh settings",
            CompositeCommand(tuple(commands)),
        )
        self.ctx.service.invalidate(part.id, mesh_only=True)
