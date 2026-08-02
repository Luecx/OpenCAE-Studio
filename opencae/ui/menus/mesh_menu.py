from opencae.ui.actions.ids import A


def build(menu_bar, actions):
    menu = menu_bar.addMenu("&Mesh")
    menu.addAction(actions.get(A.DEFAULT_SEED))
    menu.addAction(actions.get(A.EDGE_SEED))
    menu.addAction(actions.get(A.MESH_CONTROL))
    menu.addSeparator()
    menu.addAction(actions.get(A.MESH_SETTINGS))
    menu.addAction(actions.get(A.GENERATE_MESH))
    menu.addAction(actions.get(A.CLEAR_MESH))
    menu.addSeparator()
    menu.addAction(actions.get(A.EDIT_ELEMENTS))
    return menu
