"""Internal configuration helpers for concrete button primitives.

Public UI code should instantiate a structurally named button class.  These
helpers only centralize repeated Qt geometry/property setup; they are not a
widget hierarchy and intentionally own no application behavior.
"""

from __future__ import annotations

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import QToolButton

from opencae.ui.foundation.metrics import (
    INLINE_ACTION_SIZE,
    PRIMARY_CONTROL_HEIGHT,
    RESULTS_RIBBON_BUTTON_HEIGHT,
    RESULTS_RIBBON_BUTTON_WIDTH,
    RESULTS_RIBBON_ICON_SIZE,
    RIBBON_BUTTON_HEIGHT,
    RIBBON_BUTTON_WIDTH,
    RIBBON_ICON_SIZE,
    VIEWPORT_TOOL_HEIGHT,
)


def configure_ribbon(button: QToolButton) -> None:
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
    button.setIconSize(QSize(RIBBON_ICON_SIZE, RIBBON_ICON_SIZE))
    button.setFixedSize(RIBBON_BUTTON_WIDTH, RIBBON_BUTTON_HEIGHT)
    button.setProperty("ribbonButton", True)


def configure_results_ribbon(button: QToolButton, *, width: int | None = None) -> None:
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
    button.setIconSize(QSize(RESULTS_RIBBON_ICON_SIZE, RESULTS_RIBBON_ICON_SIZE))
    button.setFixedSize(int(width or RESULTS_RIBBON_BUTTON_WIDTH), RESULTS_RIBBON_BUTTON_HEIGHT)
    button.setProperty("ribbonButton", True)
    button.setProperty("resultsRibbonButton", True)


def configure_viewport(button: QToolButton) -> None:
    button.setProperty("viewportTool", True)
    button.setFixedHeight(VIEWPORT_TOOL_HEIGHT)


def configure_inline(button: QToolButton) -> None:
    button.setProperty("inlineAction", True)
    button.setFixedSize(INLINE_ACTION_SIZE, INLINE_ACTION_SIZE)


def configure_field_action(button: QToolButton) -> None:
    button.setProperty("inlineAction", True)
    button.setFixedHeight(PRIMARY_CONTROL_HEIGHT)


def configure_compact(button: QToolButton, *, size: int = 28) -> None:
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setFixedSize(int(size), int(size))
