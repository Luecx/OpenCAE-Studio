"""Recover beam surface normal stress from local section resultants."""

from __future__ import annotations

import numpy as np


_NORMAL_ALIASES = {"N", "NX", "F1", "FX", "SF1", "AXIAL", "NORMAL"}
_MY_ALIASES = {"MY", "M2", "SM2", "BM2"}
_MZ_ALIASES = {"MZ", "M3", "SM3", "BM3"}
_HINTS = ("BEAM", "SECTION", "SECT", "ELFOR", "INTERNAL", "FORCE")
_NORMAL_STRESS_COMPONENTS = {"SXX", "XX", "S11", "SIGMAXX"}
_ZERO_STRESS_COMPONENTS = {
    "SYY", "SZZ", "SYZ", "SZY", "SZX", "SXZ", "SXY", "SYX",
    "YY", "ZZ", "YZ", "ZY", "ZX", "XZ", "XY", "YX",
    "S22", "S33", "S23", "S32", "S31", "S13", "S12", "S21",
}


def stress_coefficients(properties, y: float, z: float) -> tuple[float, float, float]:
    """Return coefficients for ``sigma11 = cN*N + cM2*M2 + cM3*M3``.

    FEMaster reports beam section resultants in the local section frame
    ``[N, V2, V3, T, M2, M3]``.  Its profile convention is
    ``I22 = integral(z^2 dA)``, ``I33 = integral(y^2 dA)`` and
    ``I23 = integral(y*z dA)``.  With positive tension and moments taken from
    the positive local-1 cut face, equilibrium gives

        M2 =  integral(z * sigma11 dA)
        M3 = -integral(y * sigma11 dA)

    and therefore

        sigma11 = N/A
                + M2 * (I33*z - I23*y) / D
                + M3 * (I23*z - I22*y) / D,

    where ``D = I22*I33 - I23^2``.
    """
    area = float(properties.get("Area", 0.0) or 0.0)
    i22 = float(properties.get("Iyy", 0.0) or 0.0)
    i33 = float(properties.get("Izz", 0.0) or 0.0)
    i23 = float(properties.get("Iyz", 0.0) or 0.0)
    axial = 1.0 / area if abs(area) > 1.0e-18 else 0.0
    determinant = i22 * i33 - i23 * i23
    if abs(determinant) <= 1.0e-24:
        return axial, 0.0, 0.0
    m2 = (i33 * z - i23 * y) / determinant
    m3 = (i23 * z - i22 * y) / determinant
    return axial, m2, m3


def recover_normal_stress(
    grid,
    source_a: np.ndarray,
    source_b: np.ndarray,
    xi: np.ndarray,
    coefficients: np.ndarray,
    *,
    solver_element_ids: np.ndarray | None = None,
    element_nodal_forces: dict[int, np.ndarray] | None = None,
) -> np.ndarray | None:
    """Recover signed axial+bending stress at generated beam surface points."""
    if solver_element_ids is not None and element_nodal_forces:
        recovered = _from_element_nodal(
            solver_element_ids,
            xi,
            coefficients,
            element_nodal_forces,
        )
        if recovered is not None:
            return recovered

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
    """Map recovered beam normal stress onto one displayed stress component.

    Physical beam recovery currently provides only local axial/bending normal
    stress. It therefore maps to SXX. The remaining tensor components are zero;
    scalar magnitudes/equivalent stress use ``abs(SXX)``.
    """
    text = str(name or "")
    component = _canonical(text.split(":", 1)[-1])
    if component in _NORMAL_STRESS_COMPONENTS:
        return np.asarray(values, dtype=float)
    if component in _ZERO_STRESS_COMPONENTS:
        return np.zeros_like(values, dtype=float)
    if any(token in component for token in ("MISES", "MAGNITUDE", "ABS", "TRESCA")):
        return np.abs(values)
    if component in {"P1", "MAXPRINCIPAL", "PRINCIPAL1"}:
        return np.maximum(values, 0.0)
    if component in {"P2", "MIDPRINCIPAL", "PRINCIPAL2"}:
        return np.zeros_like(values, dtype=float)
    if component in {"P3", "MINPRINCIPAL", "PRINCIPAL3"}:
        return np.minimum(values, 0.0)
    return np.zeros_like(values, dtype=float)


def _from_element_nodal(
    solver_element_ids: np.ndarray,
    xi: np.ndarray,
    coefficients: np.ndarray,
    forces: dict[int, np.ndarray],
) -> np.ndarray | None:
    """Interpolate FEMaster [N,Vy,Vz,T,My,Mz] rows along every beam."""
    result = np.full(len(solver_element_ids), np.nan, dtype=float)
    found = False
    for element_id in np.unique(solver_element_ids):
        rows = forces.get(int(element_id))
        if rows is None or len(rows) == 0:
            continue
        mask = solver_element_ids == element_id
        local_xi = xi[mask]
        first = np.asarray(rows[0], dtype=float)
        second = np.asarray(rows[min(1, len(rows) - 1)], dtype=float)
        resultants = (1.0 - local_xi[:, None]) * first + local_xi[:, None] * second
        coeff = coefficients[mask]
        result[mask] = (
            coeff[:, 0] * resultants[:, 0]
            + coeff[:, 1] * resultants[:, 4]
            + coeff[:, 2] * resultants[:, 5]
        )
        found = True
    return result if found else None


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
