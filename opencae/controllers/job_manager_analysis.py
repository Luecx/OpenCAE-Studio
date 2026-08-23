"""Runs and completes Analysis-backed Jobs for JobManager.

Functions in this companion module receive the JobManager instance explicitly so
the Qt-facing class can keep its stable public methods without owning solver
preparation, runner wiring, or result construction.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from PyQt6.QtWidgets import QMessageBox

from opencae.jobs import AnalysisJobRunner
from opencae.model.core import EntityRef
from opencae.model.entities.analysis import Analysis
from opencae.model.entities.jobs import (
    Job,
    JobSourceKind,
    JobStatus,
    ResultSet,
    ResultStatus,
)

from .job_manager_factory import create_job, job_directory, utc_now
from .job_manager_results import persist_result


def run_analysis(manager, analysis_id: str) -> None:
    """Validate, persist, wire, and start one Analysis-backed Job."""
    project = manager.store.project
    analysis = project.try_resolve(analysis_id)
    if not isinstance(analysis, Analysis):
        manager.store.message.emit("The selected Analysis no longer exists")
        return

    errors = manager.validate_analysis(analysis.id, show=False)
    if errors:
        QMessageBox.warning(
            manager.parent,
            "Analysis validation",
            "\n".join(f"• {item}" for item in errors),
        )
        return

    adapter = manager.solvers.get(analysis.solver)
    if adapter is None:
        manager.store.message.emit(
            f"Solver adapter '{analysis.solver}' is unavailable"
        )
        return

    config = manager.settings.solver_config(analysis.solver)
    directory = job_directory(project, analysis.name)
    job = create_job(
        project,
        analysis,
        JobSourceKind.ANALYSIS,
        analysis.solver,
        directory,
    )
    manager.store.add_entity(
        f"Created job {job.name}",
        project.id,
        "jobs",
        job,
    )
    job = manager.store.project.resolve(job.id)
    manager.select_job(job.id)

    # The runner receives an immutable project snapshot so edits made while a
    # solver is running cannot silently alter the submitted calculation.
    runner = AnalysisJobRunner(
        deepcopy(manager.store.project),
        analysis.id,
        adapter,
        str(config.get("executable", "")),
        str(config.get("arguments", "")),
        directory,
        manager,
    )
    manager._runners[job.id] = runner
    runner.output.connect(
        lambda text, current=job.id: manager._append_output(current, text)
    )
    runner.progress.connect(
        lambda value, label, current=job.id: manager._update_progress(
            current,
            value,
            label,
        )
    )
    runner.finished.connect(
        lambda output_base, code, current=job.id, selected=adapter: finish_analysis(
            manager,
            current,
            selected,
            output_base,
            code,
        )
    )
    manager._start_job(job.id, "Starting Analysis")
    runner.start()


def finish_analysis(manager, job_id, adapter, output_base, code) -> None:
    """Finalize an Analysis Job and attach solver results when available."""
    manager._runners.pop(job_id, None)
    job = manager.store.project.try_resolve(job_id)
    if not isinstance(job, Job):
        return

    exit_code = int(code)
    completed = exit_code == 0
    candidate = deepcopy(job)
    candidate.status = (
        JobStatus.COMPLETED
        if completed
        else JobStatus.CANCELLED
        if exit_code == 130
        else JobStatus.FAILED
    )
    candidate.exit_code = exit_code
    candidate.finished_at = utc_now()
    candidate.progress = 1.0 if completed else candidate.progress
    candidate.progress_label = candidate.status.value
    manager._replace_job(candidate, f"Finished {job.name}")

    source = next(
        (
            path
            for path in adapter.result_candidates(Path(output_base))
            if path.exists()
        ),
        None,
    )
    if completed and source and source.suffix.lower() == ".frd":
        _attach_solver_result(manager, job, source)

    manager.progress_changed.emit(
        job.id,
        candidate.progress,
        candidate.progress_label,
    )
    manager.parent.refresh_action_states()


def _attach_solver_result(manager, job: Job, source: Path) -> None:
    """Read lightweight FRD metadata and persist one solver ResultSet."""
    try:
        fields = manager._result_loader.fields(source)
    except Exception as exc:
        fields = []
        manager._append_output(job.id, f"Result metadata failed: {exc}\n")

    analysis = manager.store.project.try_resolve(job.source_ref)
    steps = (
        analysis.resolved_steps(manager.store.project)
        if isinstance(analysis, Analysis)
        else ()
    )
    result = ResultSet(
        name=job.name,
        job_ref=EntityRef.of(job, "Job"),
        source_file=str(source),
        status=ResultStatus.AVAILABLE,
        fields=fields,
        metadata={
            "result_kind": "solver",
            "step_names": [step.name for step in steps],
        },
    )
    persist_result(manager.store, job.id, result)
