"""Choose a semantic button class from QAction behavior."""

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QToolButton, QWidget

from .action_button import ActionButton
from .menu_button import MenuButton
from .presentation import ButtonPresentation
from .toggle_button import ToggleButton


def button_for_action(
    action: QAction,
    *,
    presentation: ButtonPresentation = ButtonPresentation.RIBBON,
    parent: QWidget | None = None,
) -> QToolButton:
    """Render ``action`` with the primitive matching its interaction semantics."""
    if action.menu() is not None:
        return MenuButton(action=action, presentation=presentation, parent=parent)
    if action.isCheckable():
        return ToggleButton(action, presentation=presentation, parent=parent)
    return ActionButton(action, presentation=presentation, parent=parent)
