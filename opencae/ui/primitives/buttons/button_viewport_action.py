"""One-shot command button for compact viewport toolbars."""

from __future__ import annotations

from PyQt6.QtWidgets import QToolButton, QWidget

from ._configure import configure_viewport


class ButtonViewportAction(QToolButton):
    def __init__(self, text: str, *, tooltip: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setText(str(text))
        if tooltip:
            self.setToolTip(tooltip)
        self.setCheckable(False)
        configure_viewport(self)
