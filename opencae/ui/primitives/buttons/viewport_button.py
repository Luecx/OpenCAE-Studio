"""Canonical compact button used by viewport command bars."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget

from .base import SemanticToolButton
from .presentation import ButtonPresentation


class ViewportButton(SemanticToolButton):
    """Render one consistently sized action or mode in a viewport toolbar."""

    def __init__(
        self,
        text: str,
        *,
        checkable: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            text,
            checkable=checkable,
            presentation=ButtonPresentation.VIEWPORT,
            parent=parent,
        )
