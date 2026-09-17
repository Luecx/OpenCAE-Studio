"""Semantic roles used when creating concrete button primitives."""

from enum import StrEnum


class ButtonRole(StrEnum):
    """Template-level role mapped to a concrete flat button primitive."""

    DEFAULT = "default"
    PRIMARY = "primary"
    DANGER = "danger"
    TOOL = "tool"


__all__ = ["ButtonRole"]
