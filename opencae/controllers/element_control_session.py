from PyQt6.QtCore import QTimer

class ElementControlSession:
    def __init__(self, store, parent, dialogs): self.store = store; self.parent = parent; self.dialogs = dialogs

    def open(self, dialog, commit):
        viewport = getattr(self.parent, "viewport", None); previous_mode = viewport.selection_mode if viewport else "auto"
        previous_display = viewport.display_mode if viewport else "geometry"
        def mode_changed(*_):
            if viewport is None: return
            if dialog.target.source.currentText() == "Viewport Selection":
                mode = dialog.mode(); viewport.set_display_mode("mesh" if mode == "element" else "geometry"); viewport.set_selection_mode(mode)
            else:
                viewport.set_display_mode("mesh")
        dialog.target.changed.connect(mode_changed); mode_changed()
        dialog._selection_slot = lambda _value: dialog.update_selection()
        self.store.selection_changed.connect(dialog._selection_slot)
        dialog.preview_changed.connect(lambda value: self._preview(viewport, value))
        QTimer.singleShot(0, lambda: self._preview(viewport, dialog.current_preview))
        dialog.committed.connect(commit)
        dialog.finished.connect(lambda _code: self._close(dialog, viewport, previous_mode, previous_display))
        self.dialogs.append(dialog); dialog.show(); dialog.raise_(); dialog.activateWindow()

    @staticmethod
    def _preview(viewport, value):
        if viewport is None: return
        selected = value.selected if value else (); additional = (value.affected - value.selected) if value else ()
        viewport.show_element_control_preview(selected, additional)

    def _close(self, dialog, viewport, mode, display):
        if dialog in self.dialogs: self.dialogs.remove(dialog)
        try: self.store.selection_changed.disconnect(dialog._selection_slot)
        except Exception: pass
        if viewport:
            viewport.hide_element_control_preview(); viewport.set_selection_mode(mode)
            if viewport.display_mode != display: viewport.set_display_mode(display)
