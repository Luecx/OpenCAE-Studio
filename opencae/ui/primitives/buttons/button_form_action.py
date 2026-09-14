"""Standard one-shot QPushButton used in forms and dialogs."""

from __future__ import annotations

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QPushButton, QWidget


class ButtonFormAction(QPushButton):
    def __init__(
        self,
        text: str,
        *,
        icon: QIcon | None = None,
        tooltip: str = "",
        object_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(str(text), parent)
        if icon is not None:
            self.setIcon(icon)
        if tooltip:
            self.setToolTip(tooltip)
        if object_name:
            self.setObjectName(object_name)
