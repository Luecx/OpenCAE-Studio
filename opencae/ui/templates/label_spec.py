"""Defines immutable construction data for reusable label templates."""

from dataclasses import dataclass

from .label_role import LabelRole


@dataclass(frozen=True, slots=True)
class LabelSpec:
    """Text, semantic role, and tooltip used to construct one QLabel."""

    text: str
    role: LabelRole = LabelRole.BODY
    tooltip: str = ""
