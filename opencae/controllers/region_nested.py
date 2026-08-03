from opencae.ui.core.dialog_lifecycle import activate_dialog, show_modeless_dialog


def open_nested_region(context, dialog, owner, commit):
    previous = context.parent.viewport.selection_mode
    if getattr(dialog, "selection_mode", None) is not None:
        context.parent.viewport.set_selection_mode(dialog.mode())
    slot = lambda _value: dialog.update_selection()
    context.store.selection_changed.connect(slot)

    def restore():
        try: context.store.selection_changed.disconnect(slot)
        except (TypeError, RuntimeError): pass
        if getattr(dialog, "selection_mode", None) is not None:
            context.parent.viewport.set_selection_mode(previous)
        owner.show(); activate_dialog(owner)

    if getattr(dialog, "selection_mode", None) is not None:
        dialog.selection_mode.currentTextChanged.connect(lambda _text: context.parent.viewport.set_selection_mode(dialog.mode()))
    dialog.committed.connect(lambda values: (commit(values), dialog.close()))
    dialog.finished.connect(lambda _code: restore())
    show_modeless_dialog(dialog)
