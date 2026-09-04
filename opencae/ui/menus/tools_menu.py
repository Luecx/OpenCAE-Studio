"""Build the Tools menu with the single global application Settings entry."""

from opencae.ui.actions.ids import A


def build(menu_bar, actions):
    """Create Tools without duplicating solver-specific configuration actions."""
    menu = menu_bar.addMenu("&Tools")
    menu.addAction(actions.get(A.PREFERENCES))
    return menu
