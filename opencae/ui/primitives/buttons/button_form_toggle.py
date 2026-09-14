"""Persistent checkable QPushButton used in forms and dialogs."""

from __future__ import annotations

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QPushButton, QWidget


class ButtonFormToggle(QPushButton):
    def __init__(
        self,
        text: str,
        *,
        icon: QIcon | None = None,
        checked: bool = False,
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
        self.setCheckable(True)
        self.setChecked(bool(checked))
