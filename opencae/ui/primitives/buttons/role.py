"""Semantic style roles for reusable form buttons."""

from enum import StrEnum


class ButtonRole(StrEnum):
    """Semantic style role applied independently from button behavior."""

    DEFAULT = "default"
    PRIMARY = "primary"
    DANGER = "danger"
    TOOL = "tool"
