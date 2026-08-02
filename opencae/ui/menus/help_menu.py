from opencae.ui.actions.ids import A

def build(menu_bar, actions):
    menu=menu_bar.addMenu('&Help')
    menu.addAction(actions.get(A.DOCUMENTATION)); menu.addAction(actions.get(A.SHORTCUTS)); menu.addSeparator(); menu.addAction(actions.get(A.ABOUT))
    return menu
