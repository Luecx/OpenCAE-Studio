"""Evaluates topology response values and physical-density gradients."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from opencae.model.entities.optimization import OptimizationResponse, ResponseType


@dataclass(frozen=True, slots=True)
class ResponseEvaluation:
    """Scalar response value and derivative with respect to physical density."""

    value: float
    gradient: np.ndarray


def evaluate_response(
    response: OptimizationResponse,
    mask: np.ndarray,
    *,
    density: np.ndarray,
    volumes: np.ndarray,
    compliance: np.ndarray,
    density_gradient: np.ndarray,
    material_densities: np.ndarray,
) -> ResponseEvaluation:
    """Evaluate one supported response on its resolved element mask."""

    selected = np.asarray(mask, dtype=bool)
    rho = np.asarray(density, dtype=float).ravel()
    volume = np.asarray(volumes, dtype=float).ravel()
    compliance_values = np.asarray(compliance, dtype=float).ravel()
    compliance_gradient = np.asarray(density_gradient, dtype=float).ravel()
    material = np.asarray(material_densities, dtype=float).ravel()
    if not (
        len(selected)
        == len(rho)
        == len(volume)
        == len(compliance_values)
        == len(compliance_gradient)
        == len(material)
    ):
        raise ValueError(
            "Topology response arrays do not have matching lengths"
        )
    if not np.any(selected):
        raise ValueError(
            f"Response {response.name!r} has an empty element region"
        )

    gradient = np.zeros_like(rho)
    kind = ResponseType(response.response_type)
    if kind == ResponseType.STIFFNESS_ENERGY:
        gradient[selected] = compliance_gradient[selected]
        return ResponseEvaluation(
            float(np.nansum(compliance_values[selected])),
            gradient,
        )

    if np.any(~np.isfinite(volume[selected])) or np.any(
        volume[selected] <= 0.0
    ):
        raise ValueError(
            f"Response {response.name!r} contains invalid element volumes"
        )

    if kind == ResponseType.VOLUME:
        gradient[selected] = volume[selected]
        return ResponseEvaluation(
            float(np.sum(volume[selected] * rho[selected])),
            gradient,
        )

    if kind == ResponseType.VOLUME_FRACTION:
        denominator = float(np.sum(volume[selected]))
        if denominator <= 0.0:
            raise ValueError(
                f"Response {response.name!r} has zero reference volume"
            )
        gradient[selected] = volume[selected] / denominator
        return ResponseEvaluation(
            float(
                np.sum(volume[selected] * rho[selected]) / denominator
            ),
            gradient,
        )

    if np.any(~np.isfinite(material[selected])) or np.any(
        material[selected] <= 0.0
    ):
        raise ValueError(
            f"Response {response.name!r} requires a positive material density "
            "on every selected element"
        )
    mass_weights = material * volume
    if kind == ResponseType.MASS:
        gradient[selected] = mass_weights[selected]
        return ResponseEvaluation(
            float(np.sum(mass_weights[selected] * rho[selected])),
            gradient,
        )

    denominator = float(np.sum(mass_weights[selected]))
    if denominator <= 0.0:
        raise ValueError(
            f"Response {response.name!r} has zero reference mass"
        )
    gradient[selected] = mass_weights[selected] / denominator
    return ResponseEvaluation(
        float(
            np.sum(mass_weights[selected] * rho[selected]) / denominator
        ),
        gradient,
    )
