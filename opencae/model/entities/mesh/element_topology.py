"""Defines the supported topology families for mesh element controls."""

from enum import StrEnum


class ElementTopology(StrEnum):
    """Finite set of mesh topology families accepted by ElementControl."""

    LINE = "line"
    SHELL_TRI = "shell_tri"
    SHELL_QUAD = "shell_quad"
    SOLID_TET = "solid_tet"
    SOLID_PYRAMID = "solid_pyramid"
    SOLID_WEDGE = "solid_wedge"
    SOLID_HEX = "solid_hex"
