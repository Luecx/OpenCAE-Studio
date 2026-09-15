"""Analysis-job launch and result attachment helpers."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from opencae.controllers.background_task import BackgroundTask
from opencae.controllers.entity_task_guard import run_for_entity
from opencae.model.entities.jobs import Job, JobStatus, ResultSet
from opencae.model.refs import EntityRef
from opencae.results import FrdLoader
from opencae.solvers.registry import adapter_for
from opencae.utils.time import utc_now


def start_analysis(manager, job, executable, extra_arguments, directory, profile=None):
    """Create and start the immutable solver runner for one Analysis Job."""
    from opencae.jobs.analysis_job_runner import AnalysisJobRunner

    project = manager.store.project
    current = project.try_resolve(job.id)
    if not isinstance(current, Job) or current.analysis_ref is None:
        return
    analysis = project.try_resolve(current.analysis_ref)
    if analysis is None:
        manager._append_output(current.id, "Analysis no longer exists\n")
        return
    selected = adapter_for(current.solver)
    snapshot = deepcopy(project)
    runner = AnalysisJobRunner(
        snapshot,
        analysis.id,
        selected,
        executable,
        extra_arguments,
        directory,
        parent=manager,
        deck_profile=profile,
    )
    manager._runners[current.id] = runner
    runner.output.connect(lambda text, job_id=current.id: manager._append_output(job_id, text))
    runner.progress.connect(
        lambda value, label, job_id=current.id: manager._analysis_progress(job_id, value, label)
    )
    output_base = runner.output_base
    runner.finished.connect(
        lambda _base, code, job_id=current.id, adapter=selected: finish_analysis(
            manager, job_id, adapter, output_base, code
        )
    )
    manager._start_job(job.id, "Starting Analysis")
    manager.open_selected_monitor()
    runner.start()


def finish_analysis(manager, job_id, adapter, output_base, code) -> None:
    """Finalize an Analysis Job and attach only a self-contained FRD result."""
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
    manager._finish_analysis_runtime(job.id, candidate.status)

    source = next(
        (
            path
            for path in adapter.result_candidates(Path(output_base))
            if path.exists() and path.suffix.lower() == ".frd"
        ),
        None,
    )
    if completed and source is not None:
        _attach_solver_result(manager, job.id, source)

    manager.progress_changed.emit(job.id, candidate.progress, candidate.progress_label)
    manager.parent.refresh_action_states()


def _attach_solver_result(manager, job_id: str, source: Path) -> None:
    """Read FRD metadata on a worker thread before publishing the ResultSet."""
    tasks = getattr(manager, "_result_metadata_tasks", None)
    if tasks is None:
        tasks = {}
        manager._result_metadata_tasks = tasks

    previous = tasks.pop(str(job_id), None)
    if previous is not None and previous.isRunning():
        manager._append_output(
            job_id,
            "Skipped duplicate result metadata scan while one is already running\n",
        )
        tasks[str(job_id)] = previous
        return

    path = Path(source)
    task = BackgroundTask(
        lambda: FrdLoader().fields(path),
        on_result=lambda fields: run_for_entity(
            manager,
            str(job_id),
            _persist_solver_result,
            manager,
            str(job_id),
            path,
            fields,
        ),
        on_error=lambda error: run_for_entity(
            manager,
            str(job_id),
            _result_metadata_failed,
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
    manager._append_output(job_id, f"Result metadata failed: {error}\n")
    _persist_solver_result(manager, job_id, source, [])


def _persist_solver_result(manager, job_id: str, source: Path, fields) -> None:
    tasks = getattr(manager, "_result_metadata_tasks", None)
    if tasks is not None:
        tasks.pop(str(job_id), None)
    project = manager.store.project
    job = project.try_resolve(job_id)
    if not isinstance(job, Job):
        return
    analysis = project.try_resolve(job.analysis_ref) if job.analysis_ref else None
    result = ResultSet(
        name=f"{job.name} Results",
        source_file=str(source),
        fields=list(fields),
        metadata={"external": False, "analysis_id": getattr(analysis, "id", None)},
    )
    candidate = deepcopy(job)
    candidate.result_refs = [*candidate.result_refs, EntityRef(result.id)]
    manager.store.execute(
        manager._project_command(
            f"Attach {result.name}",
            lambda editable: _attach_result(editable, candidate, result),
        )
    )
    manager.results_changed.emit()


def _attach_result(project, job, result):
    project.results.append(result)
    project.jobs = [job if item.id == job.id else item for item in project.jobs]
