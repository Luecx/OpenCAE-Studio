"""Configuration-popover button for the main / Sketcher ribbon."""

from __future__ import annotations

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMenu, QToolButton, QWidget, QWidgetAction

from opencae.ui.primitives.ribbon_text import wrapped_ribbon_text
from ._configure import configure_ribbon


class ButtonRibbonOptions(QToolButton):
    """Open a QWidget-based options panel from canonical ribbon geometry."""

    def __init__(
        self,
        text: str,
        *,
        icon: QIcon | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setText(wrapped_ribbon_text(text))
        if icon is not None:
            self.setIcon(icon)
        configure_ribbon(self)
        self.setCheckable(False)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

    def set_options_panel(self, panel: QWidget) -> QMenu:
        menu = QMenu(self)
        action = QWidgetAction(menu)
        action.setDefaultWidget(panel)
        menu.addAction(action)
        self.setMenu(menu)
        return menu
