"""Validates executable Analysis and Study selections for JobManager."""

from __future__ import annotations

from pathlib import Path

from opencae.deck_formats.selection import (
    compatible_profile_ids,
    profile_display_name,
)
from opencae.model.entities.analysis import Analysis
from opencae.model.entities.optimization import TopologyOptimization
from opencae.model.entities.studies import MeshConvergenceStudy
from opencae.model.entities.mesh import DefaultSeed
from opencae.model.validation import validate_project
from opencae.optimization import validate_topology_optimization


def analysis_errors(project, analysis_id, settings, solvers) -> list[str]:
    """Return deduplicated validation errors for one Analysis execution."""
    analysis = project.try_resolve(analysis_id)
    errors: list[str] = []
    if not isinstance(analysis, Analysis):
        return ["Select an Analysis"]

    if not analysis.resolved_steps(project):
        errors.append("The Analysis does not reference any Steps")
    errors.extend(validate_project(project, analysis=analysis))

    adapter = solvers.get(analysis.solver)
    if adapter is None:
        errors.append(f"Solver adapter '{analysis.solver}' is unavailable")
    else:
        if analysis.solver not in settings.enabled_solvers():
            errors.append(f"Solver '{analysis.solver}' is disabled")
        selected_profile = str(getattr(analysis, "deck_profile_id", ""))
        if selected_profile not in compatible_profile_ids(settings, adapter):
            display = profile_display_name(settings, selected_profile)
            errors.append(
                f"Input deck profile '{display or '<not selected>'}' "
                f"is not compatible with solver '{analysis.solver}'"
            )

    executable = str(
        settings.solver_config(analysis.solver).get("executable", "")
    )
    if not Path(executable).is_file():
        errors.append(
            f"Solver executable is unavailable: {executable or '<not configured>'}"
        )

    # Several validation layers may detect the same broken reference. Preserve
    # the first diagnostic order while keeping the UI message concise.
    return list(dict.fromkeys(errors))


def study_errors(project, study_id, settings=None, solvers=None) -> list[str]:
    """Validate topology or an automatic mesh-convergence study."""
    study = project.try_resolve(study_id)
    if isinstance(study, MeshConvergenceStudy):
        errors = []
        analysis = project.try_resolve(study.analysis_ref)
        if not isinstance(analysis, Analysis):
            errors.append("Choose a valid Analysis")
        if study.step_id < 1:
            errors.append("Step ID must be positive")
        if not study.metrics:
            errors.append("Add a Displacement Control")
        valid_components = {"Magnitude", "D1", "D2", "D3", "D4", "D5", "D6"}
        ids, names = set(), set()
        for control in study.metrics:
            if control.get("kind") != "displacement_control":
                errors.append("Only Displacement Controls are supported")
            if control.get("component") not in valid_components:
                errors.append("Displacement component must be D1–D6 or Magnitude")
            if not control.get("name") or control.get("name") in names:
                errors.append("Displacement Control names must be unique and nonempty")
            if not control.get("id") or control.get("id") in ids:
                errors.append("Displacement Control IDs must be unique and nonempty")
            ids.add(control.get("id"))
            names.add(control.get("name"))
            for node in control.get("nodes", ()):
                if len(node.get("position", ())) != 3:
                    errors.append("Selected nodes must have original X, Y, Z positions")
        scales = study.mesh_scales
        if len(scales) < 3 or any(scale <= 0 for scale in scales) or any(
            a <= b for a, b in zip(scales, scales[1:])
        ):
            errors.append("Specify at least three strictly decreasing positive mesh scales")
        if not 0 < study.relative_tolerance < 1:
            errors.append("Tolerance must be between 0 and 1")
        for part in project.parts:
            if part.mesh.element_count and not part.geometry:
                errors.append(f"Orphan-mesh Part {part.name} cannot be remeshed")
            if part.geometry and not any(isinstance(seed, DefaultSeed) for seed in part.mesh.seeds):
                errors.append(f"Part {part.name} requires a default mesh-size seed")
        if not project.parts or not any(part.geometry for part in project.parts):
            errors.append("The Study needs at least one meshed CAD Part")
        if isinstance(analysis, Analysis) and solvers is not None:
            adapter = solvers.get(analysis.solver)
            if adapter is not None and not any(
                candidate.suffix.casefold() == ".frd"
                for candidate in adapter.result_candidates(Path("probe"))
            ):
                errors.append(
                    f"Solver {analysis.solver} does not expose FRD results; "
                    "this Study requires an FRD-producing solver"
                )
        if isinstance(analysis, Analysis) and settings is not None and solvers is not None:
            errors.extend(analysis_errors(project, analysis.id, settings, solvers))
        return list(dict.fromkeys(errors))
    if not isinstance(study, TopologyOptimization):
        return ["Select an executable Study"]

    errors, *_ = validate_topology_optimization(
        project,
        study,
        build_operators=False,
    )
    return list(dict.fromkeys(errors))
