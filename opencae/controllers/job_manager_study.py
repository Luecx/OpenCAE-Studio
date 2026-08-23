"""Runs and completes topology Study-backed Jobs for JobManager."""

from __future__ import annotations

from copy import deepcopy

import numpy as np
from PyQt6.QtWidgets import QMessageBox

from opencae.model.core import EntityRef
from opencae.model.entities.jobs import (
    Job,
    JobSourceKind,
    JobStatus,
    ResultSet,
    ResultStatus,
)
from opencae.model.entities.optimization import OptimizationRun, TopologyOptimization
from opencae.optimization import TopologyOptimizationRunner

from .job_manager_factory import create_job, job_directory, utc_now
from .job_manager_results import persist_result


def run_study(manager, study_id: str) -> None:
    """Validate, persist, wire, and start one topology Study-backed Job."""
    project = manager.store.project
    study = project.try_resolve(study_id)
    if not isinstance(study, TopologyOptimization):
        manager.store.message.emit("The selected Study type is not executable")
        return

    errors = manager.validate_study(study.id, show=False)
    if errors:
        QMessageBox.warning(
            manager.parent,
            "Study validation",
            "\n".join(f"• {item}" for item in errors),
        )
        return

    adapter = manager.solvers.get("FEMaster")
    if adapter is None:
        manager.store.message.emit("Solver adapter 'FEMaster' is unavailable")
        return

    config = manager.settings.solver_config("FEMaster")
    directory = job_directory(project, study.name)
    job = create_job(
        project,
        study,
        JobSourceKind.STUDY,
        "FEMaster",
        directory,
    )
    manager.store.add_entity(
        f"Created job {job.name}",
        project.id,
        "jobs",
        job,
    )
    job = manager.store.project.resolve(job.id)

    run = OptimizationRun(
        name=job.name,
        job_ref=EntityRef.of(job, "Job"),
        status=JobStatus.PREPARED,
        directory=str(directory),
    )
    manager.store.add_entity(
        f"Prepared topology state for {job.name}",
        study.id,
        "runs",
        run,
    )
    run = manager.store.project.resolve(run.id)
    manager.select_job(job.id)

    # As with Analysis Jobs, the optimization evaluates a stable project
    # snapshot while iteration entities are persisted through the live store.
    runner = TopologyOptimizationRunner(
        manager.store,
        deepcopy(manager.store.project),
        study.id,
        run.id,
        adapter,
        str(config.get("executable", "")),
        str(config.get("arguments", "")),
        directory,
        manager,
    )
    manager._runners[job.id] = runner
    runner.progress.connect(
        lambda text, current=job.id: manager._study_output(current, text)
    )
    runner.iteration_ready.connect(
        lambda run_id, iteration_id, mesh_index, density, current=job.id: study_iteration(
            manager,
            current,
            run_id,
            iteration_id,
            mesh_index,
            density,
        )
    )
    runner.finished.connect(
        lambda status, message, current=job.id, run_id=run.id: finish_study(
            manager,
            current,
            run_id,
            status,
            message,
        )
    )
    manager._start_job(job.id, "Initializing Study")
    runner.start()


def study_iteration(
    manager,
    job_id,
    run_id,
    iteration_id,
    mesh_index,
    density,
) -> None:
    """Translate one completed topology iteration into shared Job progress."""
    run = manager.store.project.try_resolve(run_id)
    iteration = manager.store.project.try_resolve(iteration_id)
    job = manager.store.project.try_resolve(job_id)
    study = (
        manager.store.project.try_resolve(job.source_ref)
        if isinstance(job, Job)
        else None
    )
    if not isinstance(job, Job) or run is None or iteration is None:
        return

    maximum = max(
        int(
            getattr(
                getattr(study, "control_settings", None),
                "maximum_iterations",
                1,
            )
        ),
        1,
    )
    progress = min(float(iteration.number) / maximum, 0.99)
    label = f"Iteration {iteration.number}"
    manager._update_progress(job.id, progress, label)
    manager.topology_frame.emit(
        job.id,
        run,
        iteration,
        mesh_index,
        np.asarray(density, dtype=float).copy(),
    )


def finish_study(manager, job_id, run_id, status, message="") -> None:
    """Finalize a Study Job and publish density-history Results."""
    manager._runners.pop(job_id, None)
    job = manager.store.project.try_resolve(job_id)
    run = manager.store.project.try_resolve(run_id)
    if not isinstance(job, Job):
        return

    if message:
        manager._study_output(job.id, message)

    final_status = JobStatus.coerce(status)
    candidate = deepcopy(job)
    candidate.status = final_status
    candidate.finished_at = utc_now()
    candidate.progress = (
        1.0 if final_status is JobStatus.COMPLETED else candidate.progress
    )
    candidate.progress_label = final_status.value
    manager._replace_job(candidate, f"Finished {job.name}")

    if isinstance(run, OptimizationRun) and run.iterations:
        _attach_topology_result(manager, job, run)

    manager.progress_changed.emit(
        job.id,
        candidate.progress,
        candidate.progress_label,
    )
    manager.parent.refresh_action_states()


def _attach_topology_result(manager, job: Job, run: OptimizationRun) -> None:
    """Persist topology iteration history as one shared ResultSet."""
    frames = [
        {
            "number": item.number,
            "density_file": item.density_file,
            "objective": item.objective_value,
            "constraints": dict(item.constraint_values),
            "maximum_density_change": item.maximum_density_change,
            "converged": item.converged,
        }
        for item in run.iterations
    ]
    result = ResultSet(
        name=job.name,
        job_ref=EntityRef.of(job, "Job"),
        source_file="",
        status=ResultStatus.AVAILABLE,
        metadata={
            "result_kind": "topology_density",
            "study_ref": job.source_ref.entity_id if job.source_ref else "",
            "run_ref": run.id,
            "mesh_fingerprint": run.mesh_fingerprint,
            "frames": frames,
        },
    )
    persist_result(manager.store, job.id, result)
