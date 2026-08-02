from __future__ import annotations


class RegionDialogSession:
    def __init__(self, store, parent, dialogs):
        self.store = store
        self.parent = parent
        self.dialogs = dialogs

    def open(self, dialog, commit):
        viewport = getattr(self.parent, "viewport", None)
        previous_mode = viewport.selection_mode if viewport else "auto"

        def mode_changed(_text=""):
            if viewport:
                viewport.set_selection_mode(dialog.mode())

        if getattr(dialog, "selection_mode", None) is not None:
            dialog.selection_mode.currentTextChanged.connect(mode_changed)
            mode_changed()
        if viewport:
            viewport.highlight_members(dialog.members_widget.members())
        dialog._selection_slot = lambda _value, d=dialog: d.update_selection()
        self.store.selection_changed.connect(dialog._selection_slot)
        dialog.committed.connect(commit)
        dialog.finished.connect(
            lambda _code, d=dialog, mode=previous_mode: self._close(d, mode)
        )
        self.dialogs.append(dialog)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _close(self, dialog, previous_mode):
        if dialog in self.dialogs:
            self.dialogs.remove(dialog)
        try:
            self.store.selection_changed.disconnect(dialog._selection_slot)
        except Exception:
            pass
        viewport = getattr(self.parent, "viewport", None)
        if viewport:
            viewport.set_selection_mode(previous_mode)
