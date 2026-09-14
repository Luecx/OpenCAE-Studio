"""Immutable construction data for reusable form buttons."""

from dataclasses import dataclass

from PyQt6.QtGui import QIcon

from .role import ButtonRole


@dataclass(frozen=True, slots=True)
class ButtonSpec:
    """Text, style role, behavior, icon and tooltip for one form button."""

    text: str
    role: ButtonRole = ButtonRole.DEFAULT
    tooltip: str = ""
    checkable: bool = False
    icon: QIcon | None = None
