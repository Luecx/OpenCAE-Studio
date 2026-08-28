from opencae.ui.actions.ids import A
from opencae.ui.actions.spec import ActionSpec
from opencae.ui.core.icon_factory import IconKind as I


def _toggle(window, attribute):
    dock = getattr(window, attribute, None)
    if dock is not None:
        dock.setVisible(not dock.isVisible())
        if dock.isVisible():
            dock.raise_()


def specs(window):
    return (
        ActionSpec(A.FIT_VIEW,"Fit View",I.FIT_VIEW,window.fit_view,"F"),
        ActionSpec(A.TOGGLE_MESH,"Toggle Mesh Edges",I.MESH_LINES,window.toggle_mesh),
        ActionSpec(A.SHOW_PROJECT,"Project Tree",I.PART,lambda:_toggle(window, "project_dock")),
        ActionSpec(A.SHOW_JOBS,"Jobs",I.INFO,lambda:_toggle(window, "jobs_dock")),
        ActionSpec(A.SHOW_LOG,"Log",I.INFO,lambda:_toggle(window, "log_dock")),
        ActionSpec(A.SHOW_TIME_MANAGER,"Time Manager",I.INFO,lambda:_toggle(window, "time_manager_dock")),
        ActionSpec(A.RESET_LAYOUT,"Reset Layout",I.SETTINGS,window.reset_layout),
        ActionSpec(A.DOCUMENTATION,"Documentation",I.INFO,window.show_documentation),
        ActionSpec(A.SHORTCUTS,"Keyboard Shortcuts",I.INFO,window.show_shortcuts),
        ActionSpec(A.ABOUT,"About",I.INFO,window.show_about),
    )
