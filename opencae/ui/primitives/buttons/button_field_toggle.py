"""Checkable text button aligned to the 40 px primary form-control height."""

from __future__ import annotations

from PyQt6.QtWidgets import QToolButton, QWidget

from ._configure import configure_field_action


class ButtonFieldToggle(QToolButton):
    def __init__(
        self,
        text: str,
        *,
        checked: bool = False,
        tooltip: str = "",
        object_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setText(str(text))
        if tooltip:
            self.setToolTip(tooltip)
        if object_name:
            self.setObjectName(object_name)
        self.setCheckable(True)
        self.setChecked(bool(checked))
        configure_field_action(self)
