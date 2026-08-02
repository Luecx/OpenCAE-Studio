from opencae.ui.actions.ids import A

def build(menu_bar, actions):
    menu=menu_bar.addMenu('&Edit')
    menu.addAction(actions.get(A.UNDO)); menu.addAction(actions.get(A.REDO)); menu.addSeparator()
    menu.addAction(actions.get(A.EDIT_SELECTED)); menu.addAction(actions.get(A.DELETE_SELECTED))
    return menu
