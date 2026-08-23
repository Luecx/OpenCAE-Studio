"""Defines semantic presentation roles for reusable button templates."""

from enum import StrEnum


class ButtonRole(StrEnum):
    """Semantic style role applied by the shared button factory."""

    DEFAULT = "default"
    PRIMARY = "primary"
    DANGER = "danger"
    TOOL = "tool"
