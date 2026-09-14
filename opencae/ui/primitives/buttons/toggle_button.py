"""Persistent on/off QAction button."""

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QWidget

from .action_button import ActionButton
from .presentation import ButtonPresentation


class ToggleButton(ActionButton):
    """Render a persistent boolean QAction state."""

    def __init__(
        self,
        action: QAction,
        *,
        presentation: ButtonPresentation = ButtonPresentation.RIBBON,
        parent: QWidget | None = None,
    ) -> None:
        action.setCheckable(True)
        super().__init__(action, presentation=presentation, parent=parent)
