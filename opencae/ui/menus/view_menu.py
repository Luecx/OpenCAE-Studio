from opencae.ui.actions.ids import A


def build(menu_bar, actions):
    menu = menu_bar.addMenu("&View")
    menu.addAction(actions.get(A.FIT_VIEW))
    menu.addAction(actions.get(A.TOGGLE_MESH))
    return menu
