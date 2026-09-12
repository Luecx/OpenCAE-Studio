"""Build solver execution/export commands without duplicating configuration UI."""

from opencae.ui.actions.ids import A


def build(menu_bar, actions):
    """Create the operational Solver menu; configuration lives in Tools → Settings."""
    menu = menu_bar.addMenu("&Solver")
    menu.addAction(actions.get(A.PREVIEW_DECK))
    menu.addAction(actions.get(A.WRITE_DECK))
    menu.addSeparator()
    menu.addAction(actions.get(A.VALIDATE))
    menu.addAction(actions.get(A.RUN))
    return menu
