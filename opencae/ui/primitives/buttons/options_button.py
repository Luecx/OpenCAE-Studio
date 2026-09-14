"""Ribbon/tool button that opens configuration controls rather than actions."""

from __future__ import annotations

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMenu, QToolButton, QWidget, QWidgetAction

from opencae.ui.core.metrics import (
    RIBBON_BUTTON_HEIGHT,
    RIBBON_BUTTON_WIDTH,
    RIBBON_ICON_SIZE,
)
from opencae.ui.primitives.ribbon_text import wrapped_ribbon_text


class OptionsButton(QToolButton):
    """Open a configuration popover while retaining canonical ribbon styling.

    Unlike :class:`MenuButton`, the popup normally contains a QWidget form
    rather than a flat list of QActions.  The interaction distinction is useful
    for result range, deformation scaling, clipping planes, and similar tools.
    """

    def __init__(
        self,
        text: str,
        *,
        icon: QIcon | None = None,
        icon_size: int = RIBBON_ICON_SIZE,
        width: int = RIBBON_BUTTON_WIDTH,
        height: int = RIBBON_BUTTON_HEIGHT,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setText(wrapped_ribbon_text(text))
        if icon is not None:
            self.setIcon(icon)
        self.setIconSize(QSize(icon_size, icon_size))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.setProperty("ribbonButton", True)
        self.setFixedSize(width, height)
        self.setCheckable(False)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

    def set_options_panel(self, panel: QWidget) -> QMenu:
        """Install ``panel`` as the popup body and return the created menu."""
        menu = QMenu(self)
        widget_action = QWidgetAction(menu)
        widget_action.setDefaultWidget(panel)
        menu.addAction(widget_action)
        self.setMenu(menu)
        return menu
