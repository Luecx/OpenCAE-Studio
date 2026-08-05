"""Defines the supported response kinds for topology optimization."""

from enum import StrEnum


class ResponseType(StrEnum):
    """Response quantities that can be evaluated by the topology optimizer."""

    VOLUME = "volume"
    VOLUME_FRACTION = "volume_fraction"
    MASS = "mass"
    MASS_FRACTION = "mass_fraction"
    STIFFNESS_ENERGY = "stiffness_energy"
