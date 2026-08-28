"""Runs and completes Analysis-backed Jobs for JobManager.

Functions in this companion module receive the JobManager instance explicitly so
the Qt-facing class can keep its stable public methods without owning solver
preparation, runner wiring, or result construction.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from PyQt6.QtWidgets import QMessageBox

from opencae.controllers.background_task import BackgroundTask
from opencae.deck_formats.selection import (
    normalized_profile_id,
    profile_display_name,
    resolve_profile,
)
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
from opencae.results import FrdLoader

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
    profile_id = normalized_profile_id(
        manager.settings,
        adapter,
        getattr(analysis, "deck_profile_id", ""),
    )
    deck_profile = resolve_profile(manager.settings, adapter, profile_id)
    directory = job_directory(project, analysis.name)
    job = create_job(
        project,
        analysis,
        JobSourceKind.ANALYSIS,
        analysis.solver,
        directory,
    )
    job.settings["deck_profile_id"] = profile_id
    job.settings["deck_profile_name"] = profile_display_name(
        manager.settings, profile_id
    )
    if deck_profile is not None:
        job.settings["deck_profile_snapshot"] = deck_profile.to_dict()
    manager.store.add_entity(
        f"Created job {job.name}",
        project.id,
        "jobs",
        job,
    )
    job = manager.store.project.resolve(job.id)
    manager.select_job(job.id)

    # Both the model and formatter are snapshotted. Changing a custom profile
    # while the solver is running must not alter the submitted calculation.
    runner = AnalysisJobRunner(
        deepcopy(manager.store.project),
        analysis.id,
        adapter,
        str(config.get("executable", "")),
        str(config.get("arguments", config.get("extra_arguments", ""))),
        directory,
        manager,
        deck_profile=deck_profile,
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
    status = (
        JobStatus.COMPLETED
        if completed
        else JobStatus.CANCELLED
        if exit_code == 130
        else JobStatus.FAILED
    )
    progress = 1.0 if completed else job.progress
    manager._update_job_runtime(
        job.id,
        status=status,
        exit_code=exit_code,
        finished_at=utc_now(),
        progress=progress,
        progress_label=status.value,
    )

    source = next(
        (
            path
            for path in adapter.result_candidates(Path(output_base))
            if path.exists()
        ),
        None,
    )
    if completed and source and source.suffix.lower() == ".frd":
        _attach_solver_result(manager, job.id, source)

    manager.progress_changed.emit(
        job.id,
        progress,
        status.value,
    )
    manager.parent.refresh_action_states()


def _attach_solver_result(manager, job_id: str, source: Path) -> None:
    """Read potentially large FRD metadata on a worker thread."""
    tasks = getattr(manager, "_result_metadata_tasks", None)
    if tasks is None:
        tasks = {}
        manager._result_metadata_tasks = tasks

    previous = tasks.pop(str(job_id), None)
    if previous is not None and previous.isRunning():
        # A Job has one terminal result scan. This is defensive against duplicate
        # process-finished delivery without ever blocking to wait for the old one.
        manager._append_output(
            job_id,
            "Skipped duplicate result metadata scan while one is already running\n",
        )
        tasks[str(job_id)] = previous
        return

    path = Path(source)
    task = BackgroundTask(
        lambda: FrdLoader().fields(path),
        on_result=lambda fields: _persist_solver_result(
            manager,
            str(job_id),
            path,
            fields,
        ),
        on_error=lambda error: _result_metadata_failed(
            manager,
            str(job_id),
            path,
            error,
        ),
        parent=manager,
    )
    tasks[str(job_id)] = task
    manager._append_output(job_id, "Indexing solver result metadata…\n")
    task.start()


def _result_metadata_failed(manager, job_id, source, error) -> None:
    """Preserve the available result even when optional metadata indexing fails."""
    manager._append_output(job_id, f"Result metadata failed: {error}\n")
    _persist_solver_result(manager, job_id, source, [])


def _persist_solver_result(manager, job_id: str, source: Path, fields) -> None:
    """Create the lightweight ResultSet on Qt's GUI thread after indexing."""
    tasks = getattr(manager, "_result_metadata_tasks", None)
    if tasks is not None:
        tasks.pop(str(job_id), None)

    job = manager.store.project.try_resolve(job_id)
    if not isinstance(job, Job):
        return
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
        fields=list(fields or ()),
        metadata={
            "result_kind": "solver",
            "step_names": [step.name for step in steps],
            "deck_profile_id": str(job.settings.get("deck_profile_id", "")),
            "deck_profile_name": str(job.settings.get("deck_profile_name", "")),
        },
    )
    persist_result(manager.store, job.id, result)
    manager.parent.refresh_action_states()
