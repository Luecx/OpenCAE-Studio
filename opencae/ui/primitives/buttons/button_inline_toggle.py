"""Square persistent toggle beside a primary form control."""

from __future__ import annotations

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QToolButton, QWidget

from ._configure import configure_inline


class ButtonInlineToggle(QToolButton):
    def __init__(
        self,
        text: str = "",
        *,
        icon: QIcon | None = None,
        checked: bool = False,
        tooltip: str = "",
        object_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setText(str(text))
        if icon is not None:
            self.setIcon(icon)
        if tooltip:
            self.setToolTip(tooltip)
        if object_name:
            self.setObjectName(object_name)
        self.setCheckable(True)
        self.setChecked(bool(checked))
        configure_inline(self)
