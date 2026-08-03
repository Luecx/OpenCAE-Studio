from __future__ import annotations

from PyQt6.QtCore import QTimer

from opencae.ui.core.dialog_lifecycle import show_modeless_dialog


class ElementControlSession:
    """Own the preview lifecycle; picking is managed by CompactRegionSelector."""

    def __init__(self, store, parent, dialogs):
        self.store = store
        self.parent = parent
        self.dialogs = dialogs

    def open(self, dialog, commit):
        viewport = getattr(self.parent, "viewport", None)
        previous_display = viewport.display_mode if viewport else "geometry"
        if viewport:
            viewport.set_display_mode("mesh")
        dialog.preview_changed.connect(lambda value: self._preview(viewport, value))
        QTimer.singleShot(0, lambda: self._preview(viewport, dialog.current_preview))
        dialog.committed.connect(commit)
        dialog.finished.connect(
            lambda _code: self._close(dialog, viewport, previous_display)
        )
        self.dialogs.append(dialog)
        show_modeless_dialog(dialog)

    @staticmethod
    def _preview(viewport, value):
        if viewport is None:
            return
        selected = value.selected if value else ()
        additional = (value.affected - value.selected) if value else ()
        viewport.show_element_control_preview(selected, additional)

    def _close(self, dialog, viewport, display):
        if dialog in self.dialogs:
            self.dialogs.remove(dialog)
        dialog.target.finish_pick()
        if viewport:
            viewport.cancel_context_pick()
            viewport.hide_element_control_preview()
            if viewport.display_mode != display:
                viewport.set_display_mode(display)
