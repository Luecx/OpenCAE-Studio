"""Collapsed group button whose popup hosts existing widgets."""

from __future__ import annotations

from collections.abc import Iterable

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QHBoxLayout, QMenu, QToolButton, QWidget, QWidgetAction

from opencae.ui.primitives.buttons._configure import configure_ribbon
from opencae.ui.primitives.ribbon_text import wrapped_ribbon_text


class CollapsedWidgetGroupButton(QToolButton):
    """Expose an existing widget group through one canonical popup button."""

    def __init__(
        self,
        text: str,
        widgets: Iterable[QWidget],
        *,
        icon: QIcon | None = None,
        spacing: int = 2,
        property_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setText(wrapped_ribbon_text(str(text)))
        if icon is not None:
            self.setIcon(icon)
        configure_ribbon(self)
        self.setCheckable(False)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        if property_name:
            self.setProperty(property_name, True)

        menu = QMenu(self)
        panel = QWidget(menu)
        row = QHBoxLayout(panel)
        row.setContentsMargins(6, 6, 6, 6)
        row.setSpacing(int(spacing))
        for widget in tuple(widgets):
            row.addWidget(widget)
            widget.show()

        widget_action = QWidgetAction(menu)
        widget_action.setDefaultWidget(panel)
        menu.addAction(widget_action)
        self.setMenu(menu)
