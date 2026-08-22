from opencae.ui.actions.ids import A
from opencae.ui.actions.spec import ActionSpec
from opencae.ui.core.icon_factory import IconKind as I


def specs(window):
    return (
        ActionSpec(A.FIT_VIEW,"Fit View",I.FIT_VIEW,window.fit_view,"F"),
        ActionSpec(A.TOGGLE_MESH,"Toggle Mesh Edges",I.MESH,window.toggle_mesh),
        ActionSpec(A.SHOW_PROJECT,"Project Tree",I.PART,lambda:window.project_dock.setVisible(not window.project_dock.isVisible())),
        ActionSpec(A.SHOW_OUTPUT,"Output",I.INFO,lambda:window.output_dock.setVisible(not window.output_dock.isVisible())),
        ActionSpec(A.RESET_LAYOUT,"Reset Layout",I.SETTINGS,window.reset_layout),
        ActionSpec(A.DOCUMENTATION,"Documentation",I.INFO,window.show_documentation),
        ActionSpec(A.SHORTCUTS,"Keyboard Shortcuts",I.INFO,window.show_shortcuts),
        ActionSpec(A.ABOUT,"About",I.INFO,window.show_about),
    )
