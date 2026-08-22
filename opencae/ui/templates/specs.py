from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from PyQt6.QtGui import QIcon


class LabelRole(StrEnum):
    BODY = "body"
    TITLE = "title"
    MUTED = "muted"
    GROUP = "group"


class ButtonRole(StrEnum):
    DEFAULT = "default"
    PRIMARY = "primary"
    DANGER = "danger"
    TOOL = "tool"


@dataclass(frozen=True, slots=True)
class LabelSpec:
    text: str
    role: LabelRole = LabelRole.BODY
    tooltip: str = ""


@dataclass(frozen=True, slots=True)
class ButtonSpec:
    text: str
    role: ButtonRole = ButtonRole.DEFAULT
    tooltip: str = ""
    checkable: bool = False
    icon: QIcon | None = None
