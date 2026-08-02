from opencae.ui.actions.ids import A


def build(menu_bar, actions):
    menu = menu_bar.addMenu("&Geometry")
    menu.addAction(actions.get(A.NEW_PART))
    menu.addAction(actions.get(A.IMPORT_GEOMETRY))
    menu.addSeparator()
    menu.addAction(actions.get(A.PARTITION))
    menu.addAction(actions.get(A.REBUILD_GEOMETRY))
    menu.addAction(actions.get(A.SUPPRESS_FEATURE))
    menu.addSeparator()
    return menu
