from opencae.model.mesh import DefaultSeed, EdgeSeed
from opencae.ui.dialogs.default_seed import DefaultSeedDialog
from opencae.ui.dialogs.edge_seed import EdgeSeedDialog


class PartMeshSeeds:
    def __init__(self, context):
        self.ctx = context; self._dialogs = []

    def default_seed(self):
        part = self.ctx.active_part()
        if not self.ctx.require_geometry(part): return
        seed = next((item for item in part.mesh.seeds if item.seed_type == "Default"), None)
        dialog = DefaultSeedDialog(seed, self.ctx.parent)
        dialog.apply_requested.connect(lambda values, pid=part.id: self._apply_default(pid, values))
        self._open(dialog, part, preview=True)

    def edge_seed(self):
        part = self.ctx.active_part()
        if not self.ctx.require_geometry(part): return
        selected = self.ctx.selected_labels(1)
        dialog = EdgeSeedDialog(selected, parent=self.ctx.parent)
        previous_mode = self._viewport().selection_mode if self._viewport() else "auto"
        dialog.apply_requested.connect(lambda values, pid=part.id: self._apply_edge(pid, values))
        dialog._selection_slot = lambda _value, d=dialog: d.set_selected_edges(self.ctx.selected_labels(1))
        self.ctx.store.selection_changed.connect(dialog._selection_slot)
        viewport = self._viewport()
        if viewport:
            viewport.set_selection_mode("edge")
            dialog._adjust_slot = lambda label, delta, pid=part.id, d=dialog: self._adjust_edge(pid, label, delta, d)
            viewport.seed_adjust_requested.connect(dialog._adjust_slot)
        self._open(dialog, part, previous_mode=previous_mode, preview=True)

    def edit_seed(self, seed):
        if seed.seed_type == "Default": return self.default_seed()
        part = self.ctx.active_part()
        if part is None: return
        dialog = EdgeSeedDialog(seed=seed, parent=self.ctx.parent)
        dialog.apply_requested.connect(lambda values, pid=part.id, sid=seed.id: self._apply_edge(pid, values, sid))
        self._open(dialog, part, previous_mode=self._viewport().selection_mode if self._viewport() else "auto", preview=True)

    def _open(self, dialog, part, previous_mode=None, preview=False):
        self._dialogs.append(dialog)
        if preview: self._preview(part)
        dialog.finished.connect(lambda _code, d=dialog, mode=previous_mode: self._close(d, mode))
        dialog.show(); dialog.raise_(); dialog.activateWindow()

    def _close(self, dialog, previous_mode):
        if dialog in self._dialogs: self._dialogs.remove(dialog)
        try: self.ctx.store.selection_changed.disconnect(dialog._selection_slot)
        except Exception: pass
        viewport = self._viewport()
        if viewport:
            viewport.hide_seed_preview()
            try: viewport.seed_adjust_requested.disconnect(dialog._adjust_slot)
            except Exception: pass
            if previous_mode: viewport.set_selection_mode(previous_mode)

    def _apply_default(self, part_id, values):
        part = self._part(part_id)
        if part is None: return
        def update(_project):
            seed = next((item for item in part.mesh.seeds if item.seed_type == "Default"), None)
            if seed is None: seed = DefaultSeed(name=values["name"]); part.mesh.seeds.insert(0, seed)
            seed.name = values["name"]; seed.size = values["size"]
            seed.metadata = {"deviation": values["deviation"], "minimum": values["minimum"]}
            part.mesh.status = "Outdated"
        self.ctx.store.mutate("Updated default seed", update)
        self.ctx.service.invalidate(part.id, mesh_only=True); self._preview(part)

    def _apply_edge(self, part_id, values, seed_id=None):
        part = self._part(part_id); targets = self.ctx.split_labels(values["targets"])
        if part is None or not targets: self.ctx.store.message.emit("Select at least one edge"); return
        seed = next((item for item in part.mesh.seeds if item.id == seed_id), None)
        def update(_project):
            nonlocal seed
            if seed is None: seed = EdgeSeed(name=values["name"]); part.mesh.seeds.append(seed)
            for key in ("name", "method", "size", "divisions", "bias", "bias_factor"): setattr(seed, key, values[key])
            seed.targets = targets; part.mesh.status = "Outdated"
        self.ctx.store.mutate(f"Updated edge seed", update)
        self.ctx.service.invalidate(part.id, mesh_only=True); self._preview(part)

    def _adjust_edge(self, part_id, label, delta, dialog):
        part = self._part(part_id)
        if part is None: return
        seed = next((s for s in part.mesh.seeds if s.seed_type == "Edge" and label in s.targets), None)
        current = seed.divisions if seed and seed.divisions else dialog.values()["divisions"]
        value = max(1, int(current) + int(delta)); dialog.set_selected_edges((label,)); dialog.set_divisions(value)
        values = dialog.values(); values["targets"] = label; values["name"] = seed.name if seed else f"Seed {label}"
        self._apply_edge(part_id, values, seed.id if seed else None)

    def _preview(self, part):
        viewport = self._viewport()
        if viewport: viewport.show_seed_preview(part.mesh.seeds)
    def _part(self, part_id): return next((p for p in self.ctx.store.project.parts if p.id == part_id), None)
    def _viewport(self): return getattr(self.ctx.parent, "viewport", None)
