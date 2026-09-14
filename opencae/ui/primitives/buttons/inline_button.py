"""Compact action button embedded beside form fields."""

from __future__ import annotations

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QWidget

from .base import SemanticToolButton
from .presentation import ButtonPresentation


class InlineButton(SemanticToolButton):
    """A square secondary action aligned with a primary 40 px form control."""

    def __init__(
        self,
        text: str = "",
        *,
        icon: QIcon | None = None,
        tooltip: str = "",
        checkable: bool = False,
        object_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            text,
            icon=icon,
            tooltip=tooltip,
            checkable=checkable,
            presentation=ButtonPresentation.INLINE,
            object_name=object_name,
            parent=parent,
        )
