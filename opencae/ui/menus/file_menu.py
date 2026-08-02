from opencae.ui.actions.ids import A

def build(menu_bar, actions):
    menu=menu_bar.addMenu('&File')
    menu.addAction(actions.get(A.NEW_PROJECT))
    menu.addAction(actions.get(A.OPEN_PROJECT))
    menu.addAction(actions.get(A.SAVE_PROJECT))
    menu.addAction(actions.get(A.SAVE_AS))
    menu.addSeparator()
    menu.addAction(actions.get(A.IMPORT_MESH))
    menu.addAction(actions.get(A.OPEN_RESULTS))
    menu.addSeparator()
    menu.addAction(actions.get(A.PROJECT_SETTINGS))
    menu.addSeparator()
    menu.addAction(actions.get(A.QUIT))
    return menu
