"""Provides a small built-in library of common isotropic engineering materials."""

from __future__ import annotations

from opencae.units.system import UnitSystem

from .material import Material
from .material_behaviors import DensityBehavior, IsotropicElasticity

_SI = UnitSystem(
    "SI",
    length="m",
    force="N",
    time="s",
    temperature="°C",
)

# Values are representative room-temperature engineering data. They are
# deliberately basic starter definitions, not certified design allowables.
_PRESETS = (
    ("Structural Steel", 200.0e9, 0.300, 7850.0),
    ("Stainless Steel 304", 193.0e9, 0.290, 8000.0),
    ("Aluminum 6061-T6", 68.9e9, 0.330, 2700.0),
    ("Titanium Ti-6Al-4V", 113.8e9, 0.342, 4430.0),
)


def material_preset_rows(target_units: UnitSystem) -> tuple[tuple[str, float, float, float], ...]:
    """Return preset values converted from SI into ``target_units``."""
    pressure_factor, _ = _SI.conversion_to(target_units, "pressure")
    density_factor, _ = _SI.conversion_to(target_units, "density")
    return tuple(
        (
            name,
            youngs_modulus * pressure_factor,
            poisson_ratio,
            density * density_factor,
        )
        for name, youngs_modulus, poisson_ratio, density in _PRESETS
    )


def material_from_preset(
    preset_name: str,
    target_units: UnitSystem,
    *,
    name: str | None = None,
) -> Material:
    """Create one Material from a built-in preset in the active unit system."""
    row = next(
        (item for item in material_preset_rows(target_units) if item[0] == preset_name),
        None,
    )
    if row is None:
        raise KeyError(f"Unknown material preset: {preset_name}")
    label, youngs_modulus, poisson_ratio, density = row
    return Material(
        name=name or label,
        youngs_modulus=youngs_modulus,
        poisson_ratio=poisson_ratio,
        density=density,
        behaviors=[
            IsotropicElasticity(
                youngs_modulus=youngs_modulus,
                poisson_ratio=poisson_ratio,
            ),
            DensityBehavior(value=density),
        ],
    )
