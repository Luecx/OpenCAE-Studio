"""Canonical single-line text editor."""

from __future__ import annotations

from PyQt6.QtWidgets import QLineEdit, QWidget

from .geometry import apply_primary_input_geometry


class TextInput(QLineEdit):
    """A primary-height text editor with optional semantic style hook."""

    def __init__(
        self,
        value: str = "",
        *,
        placeholder: str = "",
        read_only: bool = False,
        clear_button: bool = False,
        object_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(str(value), parent)
        self.setMinimumWidth(0)
        apply_primary_input_geometry(self)
        if placeholder:
            self.setPlaceholderText(placeholder)
        self.setReadOnly(bool(read_only))
        self.setClearButtonEnabled(bool(clear_button))
        if object_name:
            self.setObjectName(object_name)
