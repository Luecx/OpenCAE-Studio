"""Defines material behavior editor metadata and model conversion helpers.

The Material dialog uses these pure helpers to keep presentation metadata out of
its widgets while preserving the existing material behavior domain classes.
"""

from __future__ import annotations

from opencae.model.entities.resources.material_behaviors import (
    DensityBehavior,
    IsotropicElasticity,
    IsotropicPlasticity,
    IsotropicThermalExpansion,
    NeoHookeElasticity,
)

CATEGORIES = ("Elasticity", "Density", "Plasticity", "Thermal expansion")

CATEGORY_ICONS = {
    "Elasticity": "E",
    "Density": "ρ",
    "Plasticity": "σ",
    "Thermal expansion": "α",
}

CATEGORY_TYPES = {
    "Elasticity": ("Isotropic elasticity", "Neo-Hooke"),
    "Density": ("Constant density",),
    "Plasticity": ("Bilinear isotropic hardening",),
    "Thermal expansion": ("Isotropic expansion",),
}

TYPE_LABELS = {
    "Isotropic elasticity": "Isotropic",
    "Neo-Hooke": "Neo-Hooke",
    "Constant density": "Constant",
    "Bilinear isotropic hardening": "Bilinear isotropic hardening",
    "Isotropic expansion": "Isotropic",
}

# key, visible label, default value, unit quantity
PROPERTY_SPECS = {
    "Isotropic elasticity": (
        ("youngs_modulus", "Young's modulus (E)", 210000.0, "pressure"),
        ("poisson_ratio", "Poisson's ratio (ν)", 0.3, None),
    ),
    "Neo-Hooke": (
        ("c10", "C10", 1.0, "pressure"),
        ("d1", "D1", 0.0, "compliance"),
    ),
    "Constant density": (
        ("value", "Density (ρ)", 0.0, "density"),
    ),
    "Bilinear isotropic hardening": (
        ("yield_stress", "Yield stress (σy)", 250.0, "pressure"),
        ("tangent_modulus", "Tangent modulus (Et)", 0.0, "pressure"),
    ),
    "Isotropic expansion": (
        ("coefficient", "Expansion coefficient (α)", 0.0, "thermal_expansion"),
        ("reference_temperature", "Reference temperature", 20.0, "temperature"),
    ),
}


def behavior_type(behavior) -> str | None:
    """Return the canonical editor type represented by a behavior object."""
    return getattr(behavior, "behavior_type", None) if behavior is not None else None


def behavior_values(behavior) -> dict[str, float]:
    """Extract editable scalar values from an existing behavior object."""
    if behavior is None:
        return {}
    kind = behavior_type(behavior)
    return {
        key: float(getattr(behavior, key))
        for key, _label, _default, _quantity in PROPERTY_SPECS.get(kind, ())
    }


def default_values(kind: str) -> dict[str, float]:
    """Return the default scalar values for a behavior type."""
    return {
        key: float(default)
        for key, _label, default, _quantity in PROPERTY_SPECS[kind]
    }


def create_behavior(kind: str, values: dict[str, float]):
    """Create the existing domain behavior represented by inline editor values."""
    factories = {
        "Isotropic elasticity": lambda: IsotropicElasticity(
            youngs_modulus=values["youngs_modulus"],
            poisson_ratio=values["poisson_ratio"],
        ),
        "Neo-Hooke": lambda: NeoHookeElasticity(
            c10=values["c10"],
            d1=values["d1"],
        ),
        "Constant density": lambda: DensityBehavior(value=values["value"]),
        "Bilinear isotropic hardening": lambda: IsotropicPlasticity(
            yield_stress=values["yield_stress"],
            tangent_modulus=values["tangent_modulus"],
        ),
        "Isotropic expansion": lambda: IsotropicThermalExpansion(
            coefficient=values["coefficient"],
            reference_temperature=values["reference_temperature"],
        ),
    }
    return factories[kind]()
