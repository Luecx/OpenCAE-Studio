from opencae.model.datums import create_datum
from opencae.model.naming import next_name
from opencae.ui.dialogs.datum_plane import DatumPlaneDialog
from opencae.ui.dialogs.datum_point import DatumPointDialog
from opencae.ui.dialogs.datum_vector import DatumVectorDialog


class PartDatums:
    def __init__(self, context): self.ctx = context; self._dialogs = []
    def datum_point(self): self._open("Point", DatumPointDialog)
    def datum_vector(self): self._open("Vector", DatumVectorDialog)
    def datum_plane(self): self._open("Plane", DatumPlaneDialog)

    def _open(self, kind, dialog_type):
        part = self.ctx.active_part()
        if part is None: return
        prefix = f"Datum {kind}"; dialog = dialog_type(next_name(prefix, part.datums), [item.name for item in part.datums], part.coordinate_systems, parent=self.ctx.parent)
        state = {"target_id": None}; self._dialogs.append(dialog)
        dialog.pick_requested.connect(lambda allowed, callback: self.ctx.parent.viewport.begin_context_pick(allowed, callback))
        dialog.preview_requested.connect(self.ctx.parent.viewport.show_datum_preview)
        dialog.apply_requested.connect(lambda values: self._commit(part.id, dialog, state, values))
        dialog.finished.connect(lambda _code: self._closed(dialog)); dialog.show(); dialog.raise_(); dialog.activateWindow()

    def _commit(self, part_id, dialog, state, values):
        part = next((item for item in self.ctx.store.project.parts if item.id == part_id), None)
        if part is None: return
        datum = create_datum(values["kind"], values["name"], values["method"], values["parameters"]); target_id = state["target_id"]
        def apply(_project):
            if target_id is None: part.datums.append(datum)
            else:
                index = next(i for i, item in enumerate(part.datums) if item.id == target_id); datum.id = target_id; part.datums[index] = datum
        self.ctx.store.mutate(f"{'Created' if target_id is None else 'Updated'} {datum.name}", apply)
        if target_id is None: state["target_id"] = datum.id
        dialog.existing_names = tuple(item.name for item in part.datums if item.id != state["target_id"])
        self.ctx.store.invalidate_scene("Datum updated")

    def _closed(self, dialog):
        self.ctx.parent.viewport.context_pick.cancel(); self.ctx.parent.viewport.hide_datum_preview()
        if dialog in self._dialogs: self._dialogs.remove(dialog)
