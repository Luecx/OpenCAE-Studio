"""Defines semantic presentation roles for reusable label templates."""

from enum import StrEnum


class LabelRole(StrEnum):
    """Semantic style role applied by the shared label factory."""

    BODY = "body"
    TITLE = "title"
    MUTED = "muted"
    GROUP = "group"
