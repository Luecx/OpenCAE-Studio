"""Immutable construction data for semantic button creation."""

from dataclasses import dataclass

from PyQt6.QtGui import QIcon

from .button_role import ButtonRole


@dataclass(frozen=True, slots=True)
class ButtonSpec:
    """Describe one button before mapping it to a concrete primitive."""

    text: str
    role: ButtonRole = ButtonRole.DEFAULT
    tooltip: str = ""
    checkable: bool = False
    icon: QIcon | None = None


__all__ = ["ButtonSpec"]
