"""Persistent toggle button for the denser Results ribbon."""

from __future__ import annotations

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QToolButton, QWidget

from ._configure import configure_results_ribbon


class ButtonResultsRibbonToggle(QToolButton):
    """Preserve Results-ribbon geometry while exposing a checked state."""

    def __init__(
        self,
        text: str,
        *,
        icon: QIcon | None = None,
        checked: bool = False,
        width: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setText(str(text))
        if icon is not None:
            self.setIcon(icon)
        self.setCheckable(True)
        self.setChecked(bool(checked))
        configure_results_ribbon(self, width=width)
