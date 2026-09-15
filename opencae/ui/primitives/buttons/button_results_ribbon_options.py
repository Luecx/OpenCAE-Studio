"""Configuration-popover button for the denser Results ribbon."""

from __future__ import annotations

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMenu, QToolButton, QWidget, QWidgetAction

from ._configure import configure_results_ribbon


class ButtonResultsRibbonOptions(QToolButton):
    """Open one Results configuration panel without changing legacy geometry."""

    def __init__(
        self,
        text: str,
        *,
        icon: QIcon | None = None,
        width: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setText(str(text))
        if icon is not None:
            self.setIcon(icon)
        configure_results_ribbon(self, width=width)
        self.setCheckable(False)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

    def set_options_panel(self, panel: QWidget) -> QMenu:
        menu = QMenu(self)
        action = QWidgetAction(menu)
        action.setDefaultWidget(panel)
        menu.addAction(action)
        self.setMenu(menu)
        return menu
