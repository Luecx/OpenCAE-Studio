"""Primary-action plus dropdown split button."""

from __future__ import annotations

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu, QToolButton, QWidget

from .action_button import ActionButton
from .presentation import ButtonPresentation


class SplitButton(ActionButton):
    """Run the default action on the main area and expose alternatives by menu."""

    def __init__(
        self,
        action: QAction,
        menu: QMenu,
        *,
        presentation: ButtonPresentation = ButtonPresentation.RIBBON,
        parent: QWidget | None = None,
    ) -> None:
        # ActionButton may inherit an action-owned menu.  The explicit menu here
        # is authoritative for split-button composition.
        super().__init__(action, presentation=presentation, parent=parent)
        self.setMenu(menu)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
