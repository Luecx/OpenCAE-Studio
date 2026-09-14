"""Persistent on/off command button."""

from __future__ import annotations

from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QWidget

from .action_button import ActionButton
from .presentation import ButtonPresentation


class ToggleButton(ActionButton):
    """Render a persistent boolean command state."""

    def __init__(
        self,
        action: QAction | None = None,
        *,
        text: str = "",
        icon: QIcon | None = None,
        tooltip: str = "",
        checked: bool | None = None,
        presentation: ButtonPresentation = ButtonPresentation.RIBBON,
        object_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        if action is not None:
            action.setCheckable(True)
        super().__init__(
            action,
            text=text,
            icon=icon,
            tooltip=tooltip,
            presentation=presentation,
            object_name=object_name,
            parent=parent,
        )
        self.setCheckable(True)
        if checked is not None:
            self.setChecked(bool(checked))
