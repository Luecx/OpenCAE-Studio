"""Recover beam surface normal stress from local section resultants."""

from __future__ import annotations

import numpy as np


_NORMAL_ALIASES = {"N", "NX", "F1", "FX", "SF1", "AXIAL", "NORMAL"}
_MY_ALIASES = {"MY", "M2", "SM2", "BM2"}
_MZ_ALIASES = {"MZ", "M3", "SM3", "BM3"}
_HINTS = ("BEAM", "SECTION", "SECT", "ELFOR", "INTERNAL", "FORCE")


def stress_coefficients(properties, y: float, z: float) -> tuple[float, float, float]:
    """Return coefficients for ``sigma = cN*N + cMy*My + cMz*Mz``."""
    area = float(properties.get("Area", 0.0) or 0.0)
    iyy = float(properties.get("Iyy", 0.0) or 0.0)
    izz = float(properties.get("Izz", 0.0) or 0.0)
    iyz = float(properties.get("Iyz", 0.0) or 0.0)
    axial = 1.0 / area if abs(area) > 1.0e-18 else 0.0
    determinant = iyy * izz - iyz * iyz
    if abs(determinant) <= 1.0e-24:
        return axial, 0.0, 0.0
    # Sign convention reduces to -My*z/Iyy + Mz*y/Izz for Iyz == 0.
    my = (iyz * y - izz * z) / determinant
    mz = (iyy * y - iyz * z) / determinant
    return axial, my, mz


def recover_normal_stress(
    grid,
    source_a: np.ndarray,
    source_b: np.ndarray,
    xi: np.ndarray,
    coefficients: np.ndarray,
) -> np.ndarray | None:
    """Recover signed axial+bending stress at generated beam surface points."""
    keys = section_force_keys(grid)
    if keys is None:
        return None
    normal_key, my_key, mz_key = keys
    count = len(source_a)
    normal = _interpolated(grid, normal_key, source_a, source_b, xi, count)
    my = _interpolated(grid, my_key, source_a, source_b, xi, count)
    mz = _interpolated(grid, mz_key, source_a, source_b, xi, count)
    return coefficients[:, 0] * normal + coefficients[:, 1] * my + coefficients[:, 2] * mz


def section_force_keys(grid) -> tuple[str | None, str | None, str | None] | None:
    """Find one coherent local-force block by component semantics, not one solver name."""
    groups: dict[str, dict[str, str]] = {}
    for key in grid.point_data.keys():
        text = str(key)
        if ":" not in text:
            continue
        block, component = text.split(":", 1)
        groups.setdefault(block, {})[_canonical(component)] = text

    ranked = []
    for block, components in groups.items():
        normal = _first(components, _NORMAL_ALIASES)
        my = _first(components, _MY_ALIASES)
        mz = _first(components, _MZ_ALIASES)
        count = sum(value is not None for value in (normal, my, mz))
        if count == 0:
            continue
        hint = 1 if any(token in block.upper() for token in _HINTS) else 0
        ranked.append((hint, count, block, normal, my, mz))
    if not ranked:
        return None
    _hint, _count, _block, normal, my, mz = max(ranked, key=lambda item: item[:2])
    return normal, my, mz


def stress_display_values(name: str | None, values: np.ndarray) -> np.ndarray:
    """Adapt signed beam normal stress to the selected stress display component."""
    upper = str(name or "").upper()
    if "MISES" in upper or "MAGNITUDE" in upper or "ABS" in upper:
        return np.abs(values)
    return values


def _interpolated(grid, key, source_a, source_b, xi, count):
    if key is None:
        return np.zeros(count, dtype=float)
    values = np.asarray(grid.point_data[key], dtype=float)
    return (1.0 - xi) * values[source_a] + xi * values[source_b]


def _canonical(value: str) -> str:
    return "".join(character for character in str(value).upper() if character.isalnum())


def _first(components: dict[str, str], aliases: set[str]) -> str | None:
    for alias in aliases:
        key = _canonical(alias)
        if key in components:
            return components[key]
    return None
