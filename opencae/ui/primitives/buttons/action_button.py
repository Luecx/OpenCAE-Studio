"""Canonical one-shot QAction-backed tool button."""

from __future__ import annotations

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QToolButton, QWidget

from opencae.ui.primitives.ribbon_text import ribbon_label, wrapped_ribbon_text

from .base import SemanticToolButton
from .presentation import ButtonPresentation


class ActionButton(SemanticToolButton):
    """Render one QAction without owning application/domain behavior."""

    def __init__(
        self,
        action: QAction,
        *,
        presentation: ButtonPresentation = ButtonPresentation.RIBBON,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(action=action, presentation=presentation, parent=parent)

        if presentation is ButtonPresentation.RIBBON:
            text, may_wrap = ribbon_label(action.text())
            self.setText(wrapped_ribbon_text(text) if may_wrap else text)

        # Preserve the established OpenCAE ribbon contract: QAction-owned menus
        # open immediately rather than requiring Qt's delayed press-and-hold.
        menu = action.menu()
        if menu is not None:
            self.setMenu(menu)
            self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
