from __future__ import annotations

from opencae.ui.core.dialog_lifecycle import show_modeless_dialog
from copy import deepcopy

from opencae.model.mesh import DefaultSeed, EdgeSeed
from opencae.model.selection import (
    RegionProjection, RegionRequirement, SelectableKind, SelectionPolicy,
    definition_from_local_labels, local_geometry_tags, region_definition_error,
)
from opencae.store.commands import CompositeCommand, UpdateFieldCommand, make_add_command, make_replace_command
from opencae.ui.dialogs.default_seed import DefaultSeedDialog
from opencae.ui.dialogs.edge_seed import EdgeSeedDialog
from ..region_selection import begin_region_pick, region_options


class PartMeshSeeds:
    def __init__(self, context):
        self.ctx = context
        self._dialogs = []

    def default_seed(self):
        part = self.ctx.active_part()
        if not self.ctx.require_geometry(part):
            return
        seed = next((item for item in part.mesh.seeds if item.seed_type == "Default"), None)
        dialog = DefaultSeedDialog(seed, self.ctx.parent)
        dialog.apply_requested.connect(lambda values, part_id=part.id: self._apply_default(part_id, values))
        self._open(dialog, part, preview=True)

    def edge_seed(self):
        part = self.ctx.active_part()
        if not self.ctx.require_geometry(part):
            return
        initial = definition_from_local_labels(part, self.ctx.selected_labels(1))
        dialog = self._edge_dialog(part, initial=initial)
        dialog.apply_requested.connect(lambda values, part_id=part.id: self._apply_edge(part_id, values))
        self._connect_adjust(dialog, part.id)
        self._open(dialog, part, preview=True)

    def edit_seed(self, seed):
        if seed.seed_type == "Default":
            return self.default_seed()
        part = self.ctx.active_part()
        if part is None:
            return
        dialog = self._edge_dialog(part, seed=seed)
        dialog.apply_requested.connect(lambda values, part_id=part.id, seed_id=seed.id: self._apply_edge(part_id, values, seed_id))
        self._connect_adjust(dialog, part.id)
        self._open(dialog, part, preview=True)

    def _edge_dialog(self, part, initial=None, seed=None):
        policy = SelectionPolicy.create(
            {SelectableKind.GEOMETRY_EDGE}, multiple=True,
            requirement=RegionRequirement(RegionProjection.ELEMENTS, (1,), 1),
        )

        def pick(_owner, done, finished):
            return begin_region_pick(self.ctx.store.project, self._viewport(), policy, done, default_owner=part, finished=finished)

        dialog = EdgeSeedDialog(
            self.ctx.store.project,
            options=region_options(
                self.ctx.store.project, owner=part, include_reference_points=False,
                projections=(RegionProjection.ELEMENTS,),
            ),
            definition=initial or getattr(seed, "target", None),
            pick_callback=pick,
            seed=seed,
            parent=self.ctx.parent,
        )
        dialog.target.set_requirement(policy.requirement, allow_part_local=True)
        preview_channel = f"edge-seed-dialog-{id(dialog)}"
        dialog._target_preview_channel = preview_channel
        dialog.target.value_changed.connect(
            lambda value: self._viewport().show_region_preview(
                preview_channel, value, color="#3296e6",
                opacity=.62, point_size=16, show_point_labels=False,
            ) if self._viewport() else None
        )
        if self._viewport():
            self._viewport().show_region_preview(
                preview_channel, dialog.target.definition(), color="#3296e6",
                opacity=.62, point_size=16, show_point_labels=False,
            )
        return dialog

    def _open(self, dialog, part, preview=False):
        self._dialogs.append(dialog)
        if preview:
            self._preview(part)
        dialog.finished.connect(lambda _code, current=dialog: self._close(current))
        show_modeless_dialog(dialog)

    def _close(self, dialog):
        if dialog in self._dialogs:
            self._dialogs.remove(dialog)
        viewport = self._viewport()
        if viewport:
            viewport.cancel_context_pick()
            channel = getattr(dialog, "_target_preview_channel", None)
            if channel:
                viewport.clear_region_preview(channel)
            viewport.hide_seed_preview()
            slot = getattr(dialog, "_adjust_slot", None)
            if slot is not None:
                try: viewport.seed_adjust_requested.disconnect(slot)
                except (TypeError, RuntimeError): pass

    def _apply_default(self, part_id, values):
        part = self._part(part_id)
        if part is None:
            return
        current = next((item for item in part.mesh.seeds if item.seed_type == "Default"), None)
        replacement = DefaultSeed(
            id=current.id if current else None,
            name=values["name"], size=values["size"],
            metadata={"deviation": values["deviation"], "minimum": values["minimum"]},
        ) if current else DefaultSeed(
            name=values["name"], size=values["size"],
            metadata={"deviation": values["deviation"], "minimum": values["minimum"]},
        )
        mutation = make_replace_command(self.ctx.store.project, part_id, "mesh.seeds", replacement) if current else make_add_command(self.ctx.store.project, part_id, "mesh.seeds", replacement)
        command = CompositeCommand((mutation, UpdateFieldCommand(part_id, "mesh.status", part.mesh.status, "Outdated")))
        self.ctx.store.execute("Updated default seed", command)
        self.ctx.service.invalidate(part_id, mesh_only=True)
        self._preview(self._part(part_id))

    def _apply_edge(self, part_id, values, seed_id=None):
        part = self._part(part_id)
        if part is None:
            return
        target = values["target"]
        requirement = RegionRequirement(RegionProjection.ELEMENTS, (1,), 1)
        error = region_definition_error(
            self.ctx.store.project, target, requirement, allow_part_local=True
        )
        if error:
            self.ctx.store.message.emit(error)
            return
        if not local_geometry_tags(part, target, 1):
            self.ctx.store.message.emit("Select at least one edge")
            return
        current = self.ctx.store.project.try_resolve(seed_id) if seed_id else None
        kwargs = {
            "name": values["name"], "target": target, "method": values["method"],
            "size": values["size"], "divisions": values["divisions"],
            "bias": values["bias"], "bias_factor": values["bias_factor"],
        }
        replacement = EdgeSeed(id=current.id, **kwargs) if current else EdgeSeed(**kwargs)
        mutation = make_replace_command(self.ctx.store.project, part_id, "mesh.seeds", replacement) if current else make_add_command(self.ctx.store.project, part_id, "mesh.seeds", replacement)
        command = CompositeCommand((mutation, UpdateFieldCommand(part_id, "mesh.status", part.mesh.status, "Outdated")))
        self.ctx.store.execute("Updated edge seed", command)
        self.ctx.service.invalidate(part_id, mesh_only=True)
        self._preview(self._part(part_id))

    def _connect_adjust(self, dialog, part_id):
        viewport = self._viewport()
        if viewport is None:
            return
        dialog._adjust_slot = lambda label, delta: self._adjust_edge(part_id, label, delta, dialog)
        viewport.seed_adjust_requested.connect(dialog._adjust_slot)

    def _adjust_edge(self, part_id, label, delta, dialog):
        part = self._part(part_id)
        if part is None:
            return
        try:
            tag = int(str(label).split("-")[-1])
        except ValueError:
            return
        seed = next((item for item in part.mesh.seeds if item.seed_type == "Edge" and tag in local_geometry_tags(part, item.target, 1)), None)
        current = seed.divisions if seed and seed.divisions else dialog.values()["divisions"]
        value = max(1, int(current) + int(delta))
        definition = definition_from_local_labels(part, (f"Edge-{tag}",))
        dialog.set_selected_definition(definition)
        dialog.set_divisions(value)
        values = dialog.values(); values["name"] = seed.name if seed else f"Seed Edge-{tag}"
        self._apply_edge(part_id, values, seed.id if seed else None)

    def _preview(self, part):
        viewport = self._viewport()
        if viewport and part:
            viewport.show_seed_preview(part.mesh.seeds)

    def _part(self, part_id): return self.ctx.store.project.try_resolve(part_id)
    def _viewport(self): return getattr(self.ctx.parent, "viewport", None)
