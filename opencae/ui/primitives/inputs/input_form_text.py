"""Canonical single-line text input used in forms and inspectors."""

from __future__ import annotations

from PyQt6.QtWidgets import QLineEdit, QWidget

from .geometry import apply_primary_input_geometry


class InputFormText(QLineEdit):
    """One 40 px text editor; composite meaning belongs outside this class."""

    def __init__(
        self,
        text: str = "",
        *,
        read_only: bool = False,
        object_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(str(text), parent)
        self.setReadOnly(bool(read_only))
        self.setMinimumWidth(0)
        if object_name:
            self.setObjectName(object_name)
        apply_primary_input_geometry(self)
