"""Canonical persistent toggle used by the main and Sketcher ribbons."""

from __future__ import annotations

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QToolButton, QWidget

from opencae.ui.primitives.ribbon_text import ribbon_label, wrapped_ribbon_text
from ._configure import configure_ribbon


class ButtonRibbonToggle(QToolButton):
    """Render one checkable QAction in the canonical ribbon geometry."""

    def __init__(self, action: QAction, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        action.setCheckable(True)
        self.setDefaultAction(action)
        configure_ribbon(self)
        text, may_wrap = ribbon_label(action.text())
        self.setText(wrapped_ribbon_text(text) if may_wrap else text)
