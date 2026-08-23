"""Defines the supported interpolation orders for mesh element controls."""

from enum import StrEnum


class ElementOrder(StrEnum):
    """Finite set of interpolation orders accepted by ElementControl."""

    FIRST = "First"
    SECOND = "Second"
