"""Defines the symmetry families supported by topology optimization."""

from enum import StrEnum


class SymmetryType(StrEnum):
    """Geometric symmetry transformations available to the optimizer."""

    PLANAR = "planar"
    ROTATIONAL = "rotational"
