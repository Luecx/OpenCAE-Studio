from opencae.ui.actions.ids import A

def build(menu_bar, actions):
    menu=menu_bar.addMenu('&Tools')
    menu.addAction(actions.get(A.PREFERENCES))
    menu.addAction(actions.get(A.SOLVER_SETTINGS))
    return menu
