"""Canonical one-shot command button."""

from __future__ import annotations

from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QToolButton, QWidget

from opencae.ui.primitives.ribbon_text import ribbon_label, wrapped_ribbon_text

from .base import SemanticToolButton
from .presentation import ButtonPresentation


class ActionButton(SemanticToolButton):
    """Render one momentary command, optionally backed by a QAction."""

    def __init__(
        self,
        action: QAction | None = None,
        *,
        text: str = "",
        icon: QIcon | None = None,
        tooltip: str = "",
        presentation: ButtonPresentation = ButtonPresentation.RIBBON,
        object_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        source_text = action.text() if action is not None else text
        super().__init__(
            text,
            action=action,
            icon=icon,
            tooltip=tooltip,
            presentation=presentation,
            object_name=object_name,
            parent=parent,
        )

        if presentation is ButtonPresentation.RIBBON:
            compact, may_wrap = ribbon_label(source_text)
            self.setText(wrapped_ribbon_text(compact) if may_wrap else compact)

        if action is not None:
            # Preserve the established OpenCAE ribbon contract: QAction-owned
            # menus open immediately rather than using delayed press-and-hold.
            menu = action.menu()
            if menu is not None:
                self.setMenu(menu)
                self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
