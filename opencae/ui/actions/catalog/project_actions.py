from opencae.ui.actions.ids import A
from opencae.ui.actions.spec import ActionSpec
from opencae.ui.core.icon_factory import IconKind as I


def specs(c, window, store):
    return (
        ActionSpec(A.NEW_PROJECT, "New Project", I.NEW_PROJECT, c.project.new, "Ctrl+N"),
        ActionSpec(A.OPEN_PROJECT, "Open Project…", I.OPEN_PROJECT, c.project.open, "Ctrl+O"),
        ActionSpec(A.OPEN_RESULTS, "Open Results…", I.RESULTS, c.project.open_results),
        ActionSpec(A.SAVE_PROJECT, "Save Project", I.SAVE, lambda: c.project.save(False), "Ctrl+S"),
        ActionSpec(A.SAVE_AS, "Save Project As…", I.SAVE, lambda: c.project.save(True), "Ctrl+Shift+S"),
        ActionSpec(A.PROJECT_SETTINGS, "Project Settings…", I.SETTINGS, c.project.settings_dialog),
        ActionSpec(A.PREFERENCES, "Preferences…", I.SETTINGS, c.project.preferences),
        ActionSpec(A.QUIT, "Quit", I.DELETE, window.close, "Ctrl+Q"),
        ActionSpec(A.UNDO, "Undo", I.UNDO, store.undo, "Ctrl+Z"),
        ActionSpec(A.REDO, "Redo", I.REDO, store.redo, "Ctrl+Y"),
        ActionSpec(A.EDIT_SELECTED, "Edit Selected…", I.EDIT, c.selection.edit_selected, "Enter"),
        ActionSpec(A.DELETE_SELECTED, "Delete Selected", I.DELETE, c.selection.delete_selected, "Delete"),
    )
