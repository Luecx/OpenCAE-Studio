from __future__ import annotations

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QHBoxLayout, QMenu, QToolButton, QWidget, QWidgetAction

from opencae.ui.core.metrics import RIBBON_BUTTON_HEIGHT, RIBBON_BUTTON_WIDTH, RIBBON_ICON_SIZE
from .primitives import action_button, wrapped_ribbon_text


def _leaf_actions(action: QAction) -> tuple[QAction, ...]:
    """Flatten one ribbon menu action to the commands the user can execute.

    Collapsed ribbon groups already provide one popup layer of their own. If a
    command inside that popup also owns a menu (Arc, More, Dimension, ...),
    showing the parent action would create an unnecessary second popup layer.
    Present the real leaf commands directly instead.
    """

    menu = action.menu()
    if menu is None:
        return (action,)
    leaves: list[QAction] = []
    for child in menu.actions():
        if child.isSeparator():
            continue
        leaves.extend(_leaf_actions(child))
    return tuple(leaves)


def action_group_button(
    text: str,
    icon_action: QAction,
    menu_actions: tuple[QAction, ...],
) -> QToolButton:
    """Large ribbon group button whose popup contains full-size action buttons."""
    button = QToolButton()
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
    button.setIcon(icon_action.icon())
    button.setIconSize(QSize(RIBBON_ICON_SIZE, RIBBON_ICON_SIZE))
    button.setFixedSize(RIBBON_BUTTON_WIDTH, RIBBON_BUTTON_HEIGHT)
    button.setText(wrapped_ribbon_text(text))
    button.setProperty("ribbonButton", True)

    menu = QMenu(button)
    panel = QWidget(menu)
    row = QHBoxLayout(panel)
    row.setContentsMargins(6, 6, 6, 6)
    row.setSpacing(2)
    for action in menu_actions:
        for leaf in _leaf_actions(action):
            action_widget = action_button(leaf)
            action_widget.clicked.connect(menu.close)
            row.addWidget(action_widget)

    widget_action = QWidgetAction(menu)
    widget_action.setDefaultWidget(panel)
    menu.addAction(widget_action)
    button.setMenu(menu)
    button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    return button
