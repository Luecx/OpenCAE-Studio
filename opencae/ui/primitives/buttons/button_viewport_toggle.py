"""Persistent mode button for compact viewport toolbars."""

from __future__ import annotations

from PyQt6.QtWidgets import QToolButton, QWidget

from ._configure import configure_viewport


class ButtonViewportToggle(QToolButton):
    def __init__(
        self,
        text: str,
        *,
        checked: bool = False,
        tooltip: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setText(str(text))
        if tooltip:
            self.setToolTip(tooltip)
        self.setCheckable(True)
        self.setChecked(bool(checked))
        configure_viewport(self)
