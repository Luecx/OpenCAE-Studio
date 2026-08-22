from opencae.ui.actions.ids import A


def build(menu_bar, actions):
    menu = menu_bar.addMenu("&Window")
    menu.addAction(actions.get(A.SHOW_PROJECT))
    menu.addAction(actions.get(A.SHOW_OUTPUT))
    menu.addSeparator()
    menu.addAction(actions.get(A.RESET_LAYOUT))
    return menu
