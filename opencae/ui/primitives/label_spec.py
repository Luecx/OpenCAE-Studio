"""Immutable construction data for semantic labels."""

from dataclasses import dataclass

from .label_role import LabelRole


@dataclass(frozen=True, slots=True)
class LabelSpec:
    """Text, role and tooltip used to construct one semantic label."""

    text: str
    role: LabelRole = LabelRole.BODY
    tooltip: str = ""
