"""Collapsed group button whose popup hosts existing widgets."""

from __future__ import annotations

from collections.abc import Iterable

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QHBoxLayout, QMenu, QWidget, QWidgetAction

from opencae.ui.primitives.buttons.button_ribbon_options import ButtonRibbonOptions


class CollapsedWidgetGroupButton(ButtonRibbonOptions):
    """Expose an existing widget group through one canonical popup button.

    This is a composite because it owns and reparents a collection of existing
    controls.  It is intentionally separate from QAction-based ribbon groups.
    """

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
        super().__init__(text, icon=icon, parent=parent)
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
