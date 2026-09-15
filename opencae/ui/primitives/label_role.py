"""Semantic presentation roles for reusable text labels."""

from enum import StrEnum


class LabelRole(StrEnum):
    """Semantic style role applied independently from label placement."""

    BODY = "body"
    TITLE = "title"
    MUTED = "muted"
    GROUP = "group"
