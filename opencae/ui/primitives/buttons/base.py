"""Shared mechanics for semantic QToolButton primitives."""

from __future__ import annotations

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QToolButton, QWidget

from opencae.ui.core.metrics import (
    INLINE_ACTION_SIZE,
    RIBBON_BUTTON_HEIGHT,
    RIBBON_BUTTON_WIDTH,
    RIBBON_ICON_SIZE,
    VIEWPORT_TOOL_HEIGHT,
)

from .presentation import ButtonPresentation


class SemanticToolButton(QToolButton):
    """Base QToolButton with centralized presentation geometry.

    Interaction subclasses decide *what* clicking means.  This class only owns
    the visual surface contract so ribbon, viewport, inline and compact buttons
    do not duplicate sizes, dynamic properties or Qt tool-button styles.
    """

    def __init__(
        self,
        text: str = "",
        *,
        action: QAction | None = None,
        icon: QIcon | None = None,
        tooltip: str = "",
        checkable: bool | None = None,
        presentation: ButtonPresentation = ButtonPresentation.DEFAULT,
        object_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._presentation = ButtonPresentation(presentation)

        if action is not None:
            self.setDefaultAction(action)
        elif text:
            self.setText(text)

        if icon is not None:
            self.setIcon(icon)
        if tooltip:
            self.setToolTip(tooltip)
        if checkable is not None:
            self.setCheckable(bool(checkable))
        if object_name:
            self.setObjectName(object_name)

        self._apply_presentation()

    @property
    def presentation(self) -> ButtonPresentation:
        """Return the visual surface contract used by this button."""
        return self._presentation

    def _apply_presentation(self) -> None:
        presentation = self._presentation
        if presentation is ButtonPresentation.RIBBON:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            self.setIconSize(QSize(RIBBON_ICON_SIZE, RIBBON_ICON_SIZE))
            self.setFixedSize(RIBBON_BUTTON_WIDTH, RIBBON_BUTTON_HEIGHT)
            self.setProperty("ribbonButton", True)
            return

        if presentation is ButtonPresentation.COMPACT:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            self.setIconSize(QSize(20, 20))
            self.setFixedSize(30, 30)
            return

        if presentation is ButtonPresentation.VIEWPORT:
            self.setProperty("viewportTool", True)
            self.setFixedHeight(VIEWPORT_TOOL_HEIGHT)
            return

        if presentation is ButtonPresentation.INLINE:
            self.setProperty("inlineAction", True)
            self.setFixedSize(INLINE_ACTION_SIZE, INLINE_ACTION_SIZE)
