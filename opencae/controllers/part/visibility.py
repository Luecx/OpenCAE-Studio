from __future__ import annotations

from PyQt6.QtCore import QTimer

from opencae.geometry.cache import CACHE
from opencae.geometry.errors import GeometryError
from opencae.geometry.orphan_mesh import snapshot_from_part
from opencae.model.selection import SelectableKind, SelectionPolicy
from opencae.ui.core.dialog_lifecycle import activate_dialog, show_modeless_dialog
from opencae.ui.dialogs.visibility import VisibilityDialog


_KIND = {
    "faces": SelectableKind.GEOMETRY_FACE,
    "cells": SelectableKind.GEOMETRY_CELL,
    "elements": SelectableKind.MESH_ELEMENT,
}


class PartVisibility:
    """Coordinate modeless Part topology visibility editing."""

    def __init__(self, context):
        self.ctx = context
        self._dialog: VisibilityDialog | None = None
        self._part_id: str | None = None
        self._visibility_refresh = None

    def visibility(self):
        part = self.ctx.active_part()
        if part is None:
            return
        if self._dialog is not None:
            if self._part_id == part.id:
                activate_dialog(self._dialog)
                return
            self._dialog.close()

        dialog = VisibilityDialog(self.ctx.parent)
        self._dialog = dialog
        self._part_id = part.id

        dialog.mode_changed.connect(
            lambda mode, pid=part.id: self._mode_changed(pid, dialog, mode)
        )
        dialog.pick_requested.connect(
            lambda mode, pid=part.id: self._begin_pick(pid, dialog, mode)
        )
        dialog.cancel_pick_requested.connect(
            self.ctx.parent.viewport.cancel_context_pick
        )
        dialog.show_selected_requested.connect(
            lambda mode, values, pid=part.id: self._show_selected(
                pid, dialog, mode, values
            )
        )
        dialog.invert_requested.connect(
            lambda mode, pid=part.id: self._invert(pid, dialog, mode)
        )
        dialog.show_all_requested.connect(
            lambda mode, pid=part.id: self._show_all(pid, dialog, mode)
        )
        dialog.hide_all_requested.connect(
            lambda mode, pid=part.id: self._hide_all(pid, dialog, mode)
        )
        dialog.finished.connect(
            lambda _code, value=dialog: self._closed(value)
        )

        refresh = lambda *_: self._refresh(dialog, part.id)
        self._visibility_refresh = refresh
        self.ctx.parent.visibility.changed.connect(refresh)

        show_modeless_dialog(dialog)
        self._mode_changed(part.id, dialog, dialog.current_mode())

    def _mode_changed(self, part_id, dialog, mode):
        part = self.ctx.store.project.try_resolve(part_id)
        if part is None or dialog is not self._dialog:
            return
        target_display = "mesh" if mode == "elements" else "geometry"
        self.ctx.parent.viewport.set_display_mode(target_display)
        self._refresh(dialog, part_id)

    def _begin_pick(self, part_id, dialog, mode):
        part = self.ctx.store.project.try_resolve(part_id)
        if part is None or dialog is not self._dialog:
            dialog.finish_pick()
            return
        universe = self._universe(part, mode)
        if not universe:
            label = mode[:-1].replace("_", " ")
            self.ctx.store.message.emit(f"No {label}s are available to hide")
            dialog.finish_pick()
            return

        target_display = "mesh" if mode == "elements" else "geometry"
        self.ctx.parent.viewport.set_display_mode(target_display)
        policy = SelectionPolicy.create({_KIND[mode]}, multiple=True)

        def selected(hit):
            value = hit.mesh_id if mode == "elements" else hit.topology_tag
            if value is None:
                return
            current = self.ctx.store.project.try_resolve(part_id)
            if current is None:
                return
            self.ctx.parent.visibility.hide_topology(part_id, mode, (int(value),))

        # Start after a pending Geometry/Mesh display switch has had a chance to
        # rebuild the scene. Re-check the button because the user can cancel the
        # request before this deferred callback runs.
        QTimer.singleShot(
            0,
            lambda: self.ctx.parent.viewport.begin_selection_session(
                policy,
                selected,
                finished=dialog.finish_pick,
            ) if (
                dialog is self._dialog
                and dialog.add_button.isChecked()
                and dialog.current_mode() == mode
            ) else None,
        )

    def _show_selected(self, part_id, dialog, mode, values):
        self._stop_pick(dialog)
        self.ctx.parent.visibility.show_topology(part_id, mode, values)

    def _invert(self, part_id, dialog, mode):
        part = self.ctx.store.project.try_resolve(part_id)
        if part is None:
            return
        self._stop_pick(dialog)
        self.ctx.parent.visibility.invert_topology(
            part_id, mode, self._universe(part, mode)
        )

    def _show_all(self, part_id, dialog, mode):
        self._stop_pick(dialog)
        self.ctx.parent.visibility.show_all_topology(part_id, mode)

    def _hide_all(self, part_id, dialog, mode):
        part = self.ctx.store.project.try_resolve(part_id)
        if part is None:
            return
        self._stop_pick(dialog)
        self.ctx.parent.visibility.hide_all_topology(
            part_id, mode, self._universe(part, mode)
        )

    def _refresh(self, dialog, part_id):
        if dialog is not self._dialog:
            return
        part = self.ctx.store.project.try_resolve(part_id)
        if part is None:
            dialog.close()
            return
        mode = dialog.current_mode()
        universe = self._universe(part, mode)
        hidden = self.ctx.parent.visibility.hidden_topology(part_id, mode)
        # Remove stale topology ids after geometry or mesh regeneration.
        stale = set(hidden) - universe
        if stale:
            self.ctx.parent.visibility.set_hidden_topology(
                part_id, mode, set(hidden) - stale
            )
            return
        dialog.set_hidden(hidden, len(universe))

    def _universe(self, part, mode) -> set[int]:
        if mode in {"faces", "cells"}:
            if not part.geometry:
                return set()
            try:
                snapshot = self.ctx.service.build_geometry(part)
            except GeometryError:
                return set()
            if mode == "faces":
                values = getattr(snapshot, "entities", {}).get(2, ())
                return {
                    int(value) for value in values
                } or {int(patch.tag) for patch in snapshot.surfaces}
            values = getattr(snapshot, "entities", {}).get(3, ())
            if values:
                return {int(value) for value in values}
            return {
                int(cell)
                for cells in snapshot.surface_to_cells.values()
                for cell in cells
            }

        snapshot = CACHE.mesh(part.id) or snapshot_from_part(part)
        if snapshot is None:
            return set()
        result = set()
        next_element_id = 1
        for block in snapshot.blocks:
            if block.dimension != snapshot.dimension:
                continue
            if block.element_tags is None:
                values = list(range(
                    next_element_id,
                    next_element_id + len(block.connectivity),
                ))
            else:
                values = [int(value) for value in block.element_tags]
            result.update(values)
            if values:
                next_element_id = max(next_element_id, max(values) + 1)
        return result

    def _stop_pick(self, dialog):
        self.ctx.parent.viewport.cancel_context_pick()
        dialog.finish_pick()

    def _closed(self, dialog):
        self.ctx.parent.viewport.cancel_context_pick()
        if self._visibility_refresh is not None:
            try:
                self.ctx.parent.visibility.changed.disconnect(
                    self._visibility_refresh
                )
            except (TypeError, RuntimeError):
                pass
        self._visibility_refresh = None
        if dialog is self._dialog:
            self._dialog = None
            self._part_id = None
