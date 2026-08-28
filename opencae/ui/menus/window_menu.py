from opencae.ui.actions.ids import A


def build(menu_bar, actions):
    menu = menu_bar.addMenu("&Window")
    menu.addAction(actions.get(A.SHOW_PROJECT))
    menu.addSeparator()
    menu.addAction(actions.get(A.SHOW_JOBS))
    menu.addAction(actions.get(A.SHOW_LOG))
    menu.addAction(actions.get(A.SHOW_TIME_MANAGER))
    menu.addSeparator()
    menu.addAction(actions.get(A.RESET_LAYOUT))
    return menu
