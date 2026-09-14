"""One-shot action button for the denser Results ribbon."""

from __future__ import annotations

from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QToolButton, QWidget

from ._configure import configure_results_ribbon


class ButtonResultsRibbonAction(QToolButton):
    """Preserve the established 70 px Results-ribbon geometry for one action."""

    def __init__(
        self,
        text: str = "",
        *,
        action: QAction | None = None,
        icon: QIcon | None = None,
        width: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if action is not None:
            self.setDefaultAction(action)
        else:
            self.setText(str(text))
            if icon is not None:
                self.setIcon(icon)
        self.setCheckable(False)
        configure_results_ribbon(self, width=width)
