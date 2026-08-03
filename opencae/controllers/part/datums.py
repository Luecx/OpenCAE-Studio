from __future__ import annotations

from opencae.model.datums import create_datum
from opencae.model.naming import next_name
from opencae.ui.dialogs.datum_plane import DatumPlaneDialog
from opencae.ui.dialogs.datum_point import DatumPointDialog
from opencae.ui.dialogs.datum_vector import DatumVectorDialog
from opencae.ui.core.dialog_lifecycle import show_modeless_dialog


class PartDatums:
    def __init__(self, context):
        self.ctx = context
        self._dialogs = []

    def datum_point(self): self._open("Point", DatumPointDialog)
    def datum_vector(self): self._open("Vector", DatumVectorDialog)
    def datum_plane(self): self._open("Plane", DatumPlaneDialog)

    def _open(self, kind, dialog_type):
        part = self.ctx.active_part()
        if part is None:
            return
        prefix = f"Datum {kind}"
        dialog = dialog_type(
            next_name(prefix, part.datums),
            [item.name for item in part.datums],
            part.coordinate_systems,
            parent=self.ctx.parent,
        )
        state = {"target_id": None}
        self._dialogs.append(dialog)
        dialog.pick_requested.connect(lambda allowed, callback, finished: self.ctx.parent.viewport.begin_datum_reference_pick(allowed, callback, finished))
        dialog.cancel_pick_requested.connect(self.ctx.parent.viewport.cancel_context_pick)
        dialog.preview_requested.connect(self.ctx.parent.viewport.show_datum_preview)
        dialog.apply_requested.connect(lambda values: self._commit(part.id, dialog, state, values))
        dialog.finished.connect(lambda _code: self._closed(dialog))
        show_modeless_dialog(dialog)

    def _commit(self, part_id, dialog, state, values):
        part = self.ctx.store.project.try_resolve(part_id)
        if part is None:
            return
        target_id = state["target_id"]
        datum = create_datum(values["kind"], values["name"], values["method"], values["parameters"], target_id)
        description = f"{'Created' if target_id is None else 'Updated'} {datum.name}"
        if target_id is None:
            self.ctx.store.add_entity(description, part_id, "datums", datum)
            state["target_id"] = datum.id
        else:
            self.ctx.store.replace_entity(description, part_id, "datums", datum)
        current_part = self.ctx.store.project.try_resolve(part_id)
        dialog.existing_names = tuple(item.name for item in current_part.datums if item.id != state["target_id"])
        current = self.ctx.store.project.try_resolve(state["target_id"])
        if current is not None:
            self.ctx.store.select(current)
        self.ctx.store.invalidate_scene("Datum updated")

    def _closed(self, dialog):
        self.ctx.parent.viewport.context_pick.cancel()
        self.ctx.parent.viewport.hide_datum_preview()
        if dialog in self._dialogs:
            self._dialogs.remove(dialog)
