from PyQt6.QtGui import QActionGroup
from PyQt6.QtWidgets import QApplication, QWidget

from opencae.ui.actions.ids import A
from opencae.ui.core.theme import (
    DEFAULT_COLOR_SCHEME,
    PALETTE,
    apply_color_scheme,
    color_scheme_label,
    color_scheme_names,
    normalize_color_scheme,
)


def build(menu_bar, actions):
    menu = menu_bar.addMenu("&View")
    menu.addAction(actions.get(A.FIT_VIEW))
    menu.addAction(actions.get(A.TOGGLE_MESH))
    menu.addSeparator()
    _add_color_scheme_menu(menu, menu_bar.parentWidget(), actions)
    return menu


def _add_color_scheme_menu(menu, window, actions) -> None:
    scheme_menu = menu.addMenu("Color Scheme")
    group = QActionGroup(scheme_menu)
    group.setExclusive(True)
    settings = getattr(getattr(window, "context", None), "settings", None)
    selected = normalize_color_scheme(
        settings.value("appearance/color_scheme", DEFAULT_COLOR_SCHEME)
        if settings is not None
        else DEFAULT_COLOR_SCHEME
    )
    for name in color_scheme_names():
        action = scheme_menu.addAction(color_scheme_label(name))
        action.setCheckable(True)
        action.setChecked(name == selected)
        action.setData(name)
        action.triggered.connect(
            lambda checked=False, scheme=name: _select_color_scheme(
                window,
                actions,
                scheme,
            )
        )
        group.addAction(action)
    # QActionGroup is parented to the menu, but retaining a named attribute also
    # makes the exclusivity owner explicit and convenient for UI tests.
    scheme_menu._color_scheme_group = group


def _select_color_scheme(window, actions, scheme: str) -> None:
    app = QApplication.instance()
    if app is None:
        return
    selected = apply_color_scheme(app, scheme)
    settings = getattr(getattr(window, "context", None), "settings", None)
    if settings is not None:
        settings.set_value("appearance/color_scheme", selected)

    refresh_icons = getattr(actions, "refresh_icons", None)
    if callable(refresh_icons):
        refresh_icons()

    viewport = getattr(window, "viewport", None)
    if viewport is not None:
        viewport.plotter.set_background(PALETTE["viewport"])
        # Rebuild CAD/mesh actors so semantic 3D colors change too. Results use
        # field colormaps rather than the UI palette, so keep their actors and
        # only update the neutral background while a result is open.
        if getattr(viewport, "stage", "") == "RESULTS":
            viewport.plotter.render()
        else:
            viewport.request_refresh()

    # Re-polish native and globally styled widgets after replacing QApplication
    # QPalette/QSS. Widgets with custom paint events read the in-place PALETTE on
    # their next update.
    if isinstance(window, QWidget):
        widgets = (window, *window.findChildren(QWidget))
        for widget in widgets:
            style = widget.style()
            style.unpolish(widget)
            style.polish(widget)
            widget.update()
