"""Immediate-popup menu button."""

from __future__ import annotations

from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QMenu, QToolButton, QWidget

from opencae.ui.primitives.ribbon_text import ribbon_label, wrapped_ribbon_text

from .base import SemanticToolButton
from .presentation import ButtonPresentation


class MenuButton(SemanticToolButton):
    """A button whose entire click target opens one menu immediately."""

    def __init__(
        self,
        text: str = "",
        *,
        menu: QMenu | None = None,
        action: QAction | None = None,
        icon: QIcon | None = None,
        presentation: ButtonPresentation = ButtonPresentation.DEFAULT,
        object_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        resolved_menu = menu if menu is not None else (action.menu() if action else None)
        super().__init__(
            text,
            action=action,
            icon=icon,
            presentation=presentation,
            object_name=object_name,
            parent=parent,
        )
        if presentation is ButtonPresentation.RIBBON:
            source_text = action.text() if action is not None else text
            compact, may_wrap = ribbon_label(source_text)
            self.setText(wrapped_ribbon_text(compact) if may_wrap else compact)
        if resolved_menu is not None:
            self.setMenu(resolved_menu)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
