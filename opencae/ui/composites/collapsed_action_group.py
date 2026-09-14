"""Collapsed ribbon group rendered as one menu button."""

from __future__ import annotations

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QHBoxLayout, QMenu, QWidget, QWidgetAction

from opencae.ui.primitives.buttons import (
    ButtonPresentation,
    MenuButton,
    button_for_action,
)


class CollapsedActionGroupButton(MenuButton):
    """One ribbon button whose popup exposes the group's full-size actions."""

    def __init__(
        self,
        text: str,
        icon_action: QAction,
        actions: tuple[QAction, ...],
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            text,
            icon=icon_action.icon(),
            presentation=ButtonPresentation.RIBBON,
            parent=parent,
        )

        menu = QMenu(self)
        panel = QWidget(menu)
        row = QHBoxLayout(panel)
        row.setContentsMargins(6, 6, 6, 6)
        row.setSpacing(2)
        for action in actions:
            action_widget = button_for_action(
                action,
                presentation=ButtonPresentation.RIBBON,
                parent=panel,
            )
            action_widget.clicked.connect(menu.close)
            row.addWidget(action_widget)

        widget_action = QWidgetAction(menu)
        widget_action.setDefaultWidget(panel)
        menu.addAction(widget_action)
        self.setMenu(menu)
