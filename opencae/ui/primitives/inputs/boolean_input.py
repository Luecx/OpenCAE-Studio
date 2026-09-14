"""Canonical boolean editor."""

from __future__ import annotations

from PyQt6.QtWidgets import QCheckBox, QWidget


class BooleanInput(QCheckBox):
    """A semantic checkbox for ordinary true/false form values."""

    def __init__(
        self,
        text: str = "",
        *,
        checked: bool = False,
        object_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(str(text), parent)
        self.setChecked(bool(checked))
        if object_name:
            self.setObjectName(object_name)
