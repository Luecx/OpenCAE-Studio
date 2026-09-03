from opencae.ui.actions.ids import A
from opencae.ui.actions.spec import ActionSpec
from opencae.ui.core.icon_factory import IconKind as I


def _toggle(window, attribute):
    dock = getattr(window, attribute, None)
    if dock is not None:
        dock.setVisible(not dock.isVisible())
        if dock.isVisible():
            dock.raise_()


def _toggle_workspace(window, name):
    controller = getattr(window, "workspace_controller", None)
    if controller is not None:
        controller.toggle(name)
        return
    _toggle(window, "workspace_dock")


def _reset_layout(window):
    window.reset_layout()
    controller = getattr(window, "workspace_controller", None)
    if controller is not None:
        controller.reset()


def _show_documentation(window):
    from opencae.ui.dialogs.help_dialogs import DocumentationDialog

    DocumentationDialog(window).exec()


def _show_shortcuts(window):
    from opencae.ui.dialogs.help_dialogs import KeyboardShortcutsDialog

    KeyboardShortcutsDialog(window.actions, window).exec()


def specs(window):
    return (
        ActionSpec(A.FIT_VIEW,"Fit View",I.FIT_VIEW,window.fit_view,"F"),
        ActionSpec(A.TOGGLE_MESH,"Toggle Mesh Edges",I.MESH_LINES,window.toggle_mesh),
        ActionSpec(A.SHOW_PROJECT,"Project Tree",I.PART,lambda:_toggle(window, "project_dock")),
        ActionSpec(A.SHOW_JOBS,"Jobs",I.INFO,lambda:_toggle_workspace(window, "jobs")),
        ActionSpec(A.SHOW_LOG,"Log",I.INFO,lambda:_toggle_workspace(window, "log")),
        ActionSpec(A.SHOW_TIME_MANAGER,"Time Manager",I.INFO,lambda:_toggle_workspace(window, "time_manager")),
        ActionSpec(A.RESET_LAYOUT,"Reset Layout",I.SETTINGS,lambda:_reset_layout(window)),
        ActionSpec(A.DOCUMENTATION,"Documentation",I.INFO,lambda:_show_documentation(window)),
        ActionSpec(A.SHORTCUTS,"Keyboard Shortcuts",I.INFO,lambda:_show_shortcuts(window)),
        ActionSpec(A.ABOUT,"About",I.INFO,window.show_about),
    )
