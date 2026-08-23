"""Validates executable Analysis and Study selections for JobManager."""

from __future__ import annotations

from pathlib import Path

from opencae.model.entities.analysis import Analysis
from opencae.model.entities.optimization import TopologyOptimization
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

    if analysis.solver not in solvers:
        errors.append(f"Solver adapter '{analysis.solver}' is unavailable")
    elif analysis.solver not in settings.enabled_solvers():
        errors.append(f"Solver '{analysis.solver}' is disabled")

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


def study_errors(project, study_id) -> list[str]:
    """Return validation errors for one executable topology Study."""
    study = project.try_resolve(study_id)
    if not isinstance(study, TopologyOptimization):
        return ["Select an executable Study"]

    errors, *_ = validate_topology_optimization(
        project,
        study,
        build_operators=False,
    )
    return list(dict.fromkeys(errors))
