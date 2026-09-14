"""Canonical instant-popup menu button for the main and Sketcher ribbons."""

from __future__ import annotations

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QToolButton, QWidget

from opencae.ui.primitives.ribbon_text import ribbon_label, wrapped_ribbon_text
from ._configure import configure_ribbon


class ButtonRibbonMenu(QToolButton):
    """Render a QAction-owned menu as an immediate ribbon popup."""

    def __init__(self, action: QAction, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setDefaultAction(action)
        configure_ribbon(self)
        text, may_wrap = ribbon_label(action.text())
        self.setText(wrapped_ribbon_text(text) if may_wrap else text)
        menu = action.menu()
        if menu is None:
            raise ValueError("ButtonRibbonMenu requires a QAction with a menu")
        self.setMenu(menu)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
