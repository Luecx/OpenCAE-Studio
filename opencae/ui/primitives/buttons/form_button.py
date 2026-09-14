"""Canonical QPushButton used in forms and dialogs."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtWidgets import QPushButton, QWidget

from .role import ButtonRole
from .spec import ButtonSpec


class FormButton(QPushButton):
    """A semantic form button with centralized style-role conventions."""

    def __init__(
        self,
        spec: ButtonSpec | str,
        *,
        role: ButtonRole = ButtonRole.DEFAULT,
        clicked: Callable | None = None,
        parent: QWidget | None = None,
    ) -> None:
        resolved = spec if isinstance(spec, ButtonSpec) else ButtonSpec(str(spec), role)
        super().__init__(resolved.text, parent)

        if resolved.role is ButtonRole.PRIMARY:
            self.setObjectName("PrimaryButton")
        elif resolved.role is ButtonRole.DANGER:
            self.setObjectName("DangerButton")

        if resolved.icon is not None:
            self.setIcon(resolved.icon)
        self.setCheckable(resolved.checkable)
        if resolved.tooltip:
            self.setToolTip(resolved.tooltip)
        if clicked is not None:
            self.clicked.connect(clicked)
