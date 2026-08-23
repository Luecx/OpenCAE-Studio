"""Defines immutable construction data for reusable button templates."""

from dataclasses import dataclass

from PyQt6.QtGui import QIcon

from .button_role import ButtonRole


@dataclass(frozen=True, slots=True)
class ButtonSpec:
    """Text, semantic role, behavior, icon, and tooltip for one QPushButton."""

    text: str
    role: ButtonRole = ButtonRole.DEFAULT
    tooltip: str = ""
    checkable: bool = False
    icon: QIcon | None = None
