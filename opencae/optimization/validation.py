"""Validates topology definitions, regions, controls, filters and symmetries."""

from __future__ import annotations

import numpy as np

from opencae.model.entities.optimization import (
    ConstraintOperator,
    ResponseType,
    SymmetryType,
)

from .filtering import build_filter_operators
from .mesh_index import build_mesh_index

_RESOURCE_TYPES = {
    ResponseType.VOLUME,
    ResponseType.VOLUME_FRACTION,
    ResponseType.MASS,
    ResponseType.MASS_FRACTION,
}


def validate_topology_optimization(
    project,
    optimization,
    *,
    build_operators=False,
):
    """Return validation errors and optionally the immutable run initialization data."""

    errors: list[str] = []
    index = None
    masks = {}
    try:
        index = build_mesh_index(project)
    except Exception as exc:
        errors.append(str(exc))
        return errors, None, masks, None

    analysis = project.try_resolve(optimization.analysis_ref)
    if analysis is None:
        errors.append("Select a Linear Static analysis")
    else:
        steps = tuple(getattr(analysis, "steps", ()) or ())
        if len(steps) != 1 or steps[0].step_type != "Linear Static":
            errors.append(
                "Topology optimization requires exactly one Linear Static step"
            )

    for label, definition in (
        ("design", optimization.design_domain),
        ("frozen_solid", optimization.frozen_solid),
        ("frozen_void", optimization.frozen_void),
    ):
        if definition.empty and label != "design":
            masks[label] = np.zeros(index.count, dtype=bool)
            continue
        try:
            masks[label] = index.mask_for(project, definition)
        except Exception as exc:
            errors.append(f"{label.replace('_', ' ').title()}: {exc}")
            masks[label] = np.zeros(index.count, dtype=bool)

    if np.any(
        masks.get("frozen_solid", False)
        & masks.get("frozen_void", False)
    ):
        errors.append("Frozen Solid and Frozen Void regions overlap")
    if np.any(
        masks.get("frozen_solid", False)
        & ~masks.get("design", False)
    ):
        errors.append("Frozen Solid must be contained in the design domain")
    if np.any(
        masks.get("frozen_void", False)
        & ~masks.get("design", False)
    ):
        errors.append("Frozen Void must be contained in the design domain")
    free_design = (
        masks.get("design", np.zeros(index.count, dtype=bool))
        & ~masks.get("frozen_solid", np.zeros(index.count, dtype=bool))
        & ~masks.get("frozen_void", np.zeros(index.count, dtype=bool))
    )
    if not np.any(free_design):
        errors.append(
            "The design domain contains no free optimization elements"
        )

    if len(optimization.objectives) != 1:
        errors.append("Create exactly one optimization objective")
    if len(optimization.filters) != 1:
        errors.append(
            "Topology optimization requires exactly one filter definition"
        )
    if len(optimization.controls) != 1:
        errors.append(
            "Topology optimization requires exactly one controls definition"
        )

    objective = optimization.objective
    if objective is None:
        objective_response = None
    else:
        objective_response = project.try_resolve(objective.response_ref)
        if objective_response not in optimization.responses:
            errors.append(
                "The objective references a response outside this optimization"
            )
        elif objective_response.response_type != ResponseType.STIFFNESS_ENERGY:
            errors.append(
                "The current OC optimizer requires a Stiffness Energy objective"
            )
        else:
            try:
                objective_mask = index.mask_for(
                    project,
                    objective_response.region,
                )
                masks[objective_response.id] = objective_mask
                if not np.all(objective_mask):
                    errors.append(
                        "Stiffness Energy currently requires the complete "
                        "exported model region"
                    )
            except Exception as exc:
                errors.append(f"Objective response: {exc}")

    active_constraints = [
        item for item in optimization.constraints if item.active
    ]
    if len(active_constraints) != 1:
        errors.append(
            "The OC optimizer currently requires exactly one active "
            "resource constraint"
        )
    else:
        constraint = active_constraints[0]
        response = project.try_resolve(constraint.response_ref)
        if response not in optimization.responses:
            errors.append(
                "The active constraint references a response outside this optimization"
            )
        elif response.response_type not in _RESOURCE_TYPES:
            errors.append(
                "The active constraint must use Volume, Volume Fraction, "
                "Mass or Mass Fraction"
            )
        else:
            try:
                masks[response.id] = index.mask_for(project, response.region)
            except Exception as exc:
                errors.append(f"Constraint response: {exc}")
            if response.response_type in {
                ResponseType.MASS,
                ResponseType.MASS_FRACTION,
            }:
                selected = masks.get(
                    response.id,
                    np.zeros(index.count, dtype=bool),
                )
                invalid_density = (
                    ~np.isfinite(index.material_densities)
                    | (index.material_densities <= 0.0)
                )
                if np.any(selected & invalid_density):
                    errors.append(
                        "Mass responses require positive material density "
                        "on every selected element"
                    )
        if constraint.operator != ConstraintOperator.LESS_EQUAL:
            errors.append(
                "The current OC optimizer supports only <= resource constraints"
            )
        if constraint.limit <= 0.0:
            errors.append("The active constraint limit must be positive")

    controls = optimization.control_settings
    if not 0.0 < controls.minimum_density < 1.0:
        errors.append(
            "Minimum density must be greater than 0 and less than 1"
        )
    if not controls.minimum_density <= controls.initial_density <= 1.0:
        errors.append(
            "Initial density must lie between minimum density and 1"
        )
    if controls.maximum_iterations < 1:
        errors.append("Maximum iterations must be at least 1")
    if controls.simp_exponent <= 0.0:
        errors.append("SIMP exponent must be positive")
    if not 0.0 < controls.move_limit <= 1.0:
        errors.append("Move limit must be in (0, 1]")

    for symmetry in optimization.symmetries:
        if not symmetry.enabled:
            continue
        kind = str(symmetry.reference.get("kind", ""))
        if symmetry.symmetry_type == SymmetryType.PLANAR:
            if kind not in {"face", "datum_plane"}:
                errors.append(
                    f"{symmetry.name}: planar symmetry requires a face "
                    "or Datum Plane"
                )
            else:
                _validate_planar_reference(symmetry, errors)
        if symmetry.symmetry_type == SymmetryType.ROTATIONAL:
            if kind not in {"edge", "datum_vector"}:
                errors.append(
                    f"{symmetry.name}: rotational symmetry requires an edge "
                    "or Datum Vector"
                )
            else:
                _validate_axis_reference(symmetry, errors)

    operators = None
    if build_operators and not errors:
        try:
            operators = build_filter_operators(
                index.centroids,
                optimization.filter_settings,
                optimization.symmetries,
                active_mask=(
                    masks["design"]
                    & ~masks["frozen_solid"]
                    & ~masks["frozen_void"]
                ),
            )
        except Exception as exc:
            errors.append(f"Filter: {exc}")

    return errors, index, masks, operators


def _validate_planar_reference(symmetry, errors):
    reference = symmetry.reference
    normal = np.asarray(
        reference.get("normal") or reference.get("direction") or (),
        dtype=float,
    )
    origin = np.asarray(
        reference.get("origin") or reference.get("point") or (),
        dtype=float,
    )
    if (
        normal.shape != (3,)
        or origin.shape != (3,)
        or np.linalg.norm(normal) <= 1.0e-14
    ):
        errors.append(
            f"{symmetry.name}: the symmetry plane has no valid origin and normal"
        )
        return
    points = np.asarray(reference.get("points") or (), dtype=float)
    if len(points) < 3:
        return
    unit = normal / np.linalg.norm(normal)
    scale = max(float(np.linalg.norm(np.ptp(points, axis=0))), 1.0)
    deviation = float(np.max(np.abs((points - origin) @ unit)))
    if deviation > scale * 1.0e-6:
        errors.append(f"{symmetry.name}: the selected face is not planar")


def _validate_axis_reference(symmetry, errors):
    reference = symmetry.reference
    direction = np.asarray(
        reference.get("direction") or (),
        dtype=float,
    )
    origin = np.asarray(
        reference.get("origin") or reference.get("point") or (),
        dtype=float,
    )
    if (
        direction.shape != (3,)
        or origin.shape != (3,)
        or np.linalg.norm(direction) <= 1.0e-14
    ):
        errors.append(
            f"{symmetry.name}: the rotation axis has no valid origin and direction"
        )
        return
    points = np.asarray(reference.get("points") or (), dtype=float)
    if len(points) < 2:
        return
    unit = direction / np.linalg.norm(direction)
    radial = (
        points
        - origin
        - ((points - origin) @ unit)[:, None] * unit[None, :]
    )
    scale = max(float(np.linalg.norm(np.ptp(points, axis=0))), 1.0)
    if float(np.max(np.linalg.norm(radial, axis=1))) > scale * 1.0e-6:
        errors.append(
            f"{symmetry.name}: rotational symmetry requires a straight edge"
        )
