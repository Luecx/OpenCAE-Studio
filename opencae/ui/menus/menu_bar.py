from . import (
    edit_menu,
    file_menu,
    geometry_menu,
    help_menu,
    mesh_menu,
    solver_menu,
    tools_menu,
    view_menu,
    window_menu,
)


def build_menus(window, actions):
    bar = window.menuBar()
    for module in (
        file_menu,
        edit_menu,
        view_menu,
        geometry_menu,
        mesh_menu,
        tools_menu,
        solver_menu,
        window_menu,
        help_menu,
    ):
        module.build(bar, actions)
