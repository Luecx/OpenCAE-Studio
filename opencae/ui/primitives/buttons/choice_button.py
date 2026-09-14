"""Exclusive mode/choice tool button."""

from __future__ import annotations

from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QWidget

from .base import SemanticToolButton
from .presentation import ButtonPresentation


class ChoiceButton(SemanticToolButton):
    """A checkable auto-exclusive button used for mutually exclusive modes."""

    def __init__(
        self,
        text: str = "",
        *,
        action: QAction | None = None,
        icon: QIcon | None = None,
        checked: bool = False,
        presentation: ButtonPresentation = ButtonPresentation.DEFAULT,
        object_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        if action is not None:
            action.setCheckable(True)
        super().__init__(
            text,
            action=action,
            icon=icon,
            checkable=True,
            presentation=presentation,
            object_name=object_name,
            parent=parent,
        )
        self.setAutoExclusive(True)
        self.setChecked(checked)
