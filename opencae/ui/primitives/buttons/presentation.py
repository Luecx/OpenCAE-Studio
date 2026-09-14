"""Presentation modes shared by semantic tool-button primitives."""

from enum import StrEnum


class ButtonPresentation(StrEnum):
    """Visual surface used to render one semantic button interaction."""

    DEFAULT = "default"
    RIBBON = "ribbon"
    COMPACT = "compact"
    VIEWPORT = "viewport"
    INLINE = "inline"
