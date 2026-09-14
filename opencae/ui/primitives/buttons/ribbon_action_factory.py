"""Route QAction semantics to one concrete flat ribbon-button primitive."""

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QToolButton, QWidget

from .button_ribbon_action import ButtonRibbonAction
from .button_ribbon_menu import ButtonRibbonMenu
from .button_ribbon_toggle import ButtonRibbonToggle


def ribbon_button_for_action(
    action: QAction,
    *,
    parent: QWidget | None = None,
) -> QToolButton:
    """Return the concrete ribbon primitive matching one QAction's behavior."""
    if action.menu() is not None:
        return ButtonRibbonMenu(action, parent=parent)
    if action.isCheckable():
        return ButtonRibbonToggle(action, parent=parent)
    return ButtonRibbonAction(action, parent=parent)


__all__ = ["ribbon_button_for_action"]
