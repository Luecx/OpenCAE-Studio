"""Collapsed ribbon group rendered as one menu button."""

from __future__ import annotations

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QHBoxLayout, QMenu, QToolButton, QWidget, QWidgetAction

from opencae.ui.primitives.buttons._configure import configure_ribbon
from opencae.ui.primitives.buttons.ribbon_action_factory import ribbon_button_for_action
from opencae.ui.primitives.ribbon_text import wrapped_ribbon_text


def _leaf_actions(action: QAction) -> tuple[QAction, ...]:
    """Return executable descendants without introducing nested popup layers."""
    menu = action.menu()
    if menu is None:
        return (action,)
    leaves: list[QAction] = []
    for child in menu.actions():
        if child.isSeparator():
            continue
        leaves.extend(_leaf_actions(child))
    return tuple(leaves)


class CollapsedActionGroupButton(QToolButton):
    """One ribbon button whose popup exposes the group's full-size actions."""

    def __init__(
        self,
        text: str,
        icon_action: QAction,
        actions: tuple[QAction, ...],
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setText(wrapped_ribbon_text(str(text)))
        self.setIcon(icon_action.icon())
        configure_ribbon(self)
        self.setCheckable(False)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        menu = QMenu(self)
        panel = QWidget(menu)
        row = QHBoxLayout(panel)
        row.setContentsMargins(6, 6, 6, 6)
        row.setSpacing(2)
        for action in actions:
            for leaf in _leaf_actions(action):
                action_widget = ribbon_button_for_action(leaf, parent=panel)
                action_widget.clicked.connect(menu.close)
                row.addWidget(action_widget)

        widget_action = QWidgetAction(menu)
        widget_action.setDefaultWidget(panel)
        menu.addAction(widget_action)
        self.setMenu(menu)
