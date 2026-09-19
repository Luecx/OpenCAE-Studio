"""Persist and execute a mesh-convergence Study through the existing Job API."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from PyQt6.QtWidgets import QMessageBox

from opencae.deck_formats.selection import (
    normalized_profile_id, resolve_profile,
)
from opencae.jobs.mesh_convergence_runner import MeshConvergenceRunner
from opencae.model.core import EntityRef
from opencae.model.entities.jobs import (
    Job, JobSourceKind, JobStatus, ResultSet, ResultStatus,
)
from opencae.model.entities.studies import MeshConvergenceStudy
from opencae.results.mesh_convergence import assess_convergence, assess_all_metrics

from .job_manager_factory import create_job, job_directory, utc_now
from .job_manager_results import persist_result
from .project_sessions import run_for_entity


def run_convergence(manager, study_id):
    project = manager.store.project
    study = project.try_resolve(study_id)
    if not isinstance(study, MeshConvergenceStudy):
        manager.store.message.emit("Select a Mesh Convergence Study")
        return
    errors = manager.validate_study(study.id, show=False)
    if errors:
        QMessageBox.warning(
            manager.parent, "Mesh Convergence validation",
            "\n".join(f"• {error}" for error in errors),
        )
        return
    if any(
        running_job.id in manager._runners
        and running_job.source_ref
        and running_job.source_ref.entity_id == study.id
        for running_job in project.jobs
    ):
        manager.store.message.emit("A mesh-convergence run is already active for this Study")
        return
    analysis = project.resolve(study.analysis_ref)
    adapter = manager.solvers[analysis.solver]
    config = manager.settings.solver_config(analysis.solver)
    profile_id = normalized_profile_id(
        manager.settings, adapter, getattr(analysis, "deck_profile_id", "")
    )
    profile = resolve_profile(manager.settings, adapter, profile_id)
    directory = job_directory(project, study.name)
    job = create_job(
        project, study, JobSourceKind.STUDY, analysis.solver, directory
    )
    job.settings["deck_profile_id"] = profile_id
    manager.store.add_entity(
        f"Created mesh-convergence Job {job.name}",
        project.id, "jobs", job,
    )
    job = manager.store.project.resolve(job.id)
    candidate = deepcopy(manager.store.project.resolve(study.id))
    candidate.run_history.append({
        "job_id": job.id,
        "started_at": utc_now(),
        "status": "Running",
        "metric": study.metric,
        "relative_tolerance": float(study.relative_tolerance),
        "exclude_radius": float(study.exclude_radius),
        "mesh_scales": list(study.mesh_scales),
        "samples": [],
        "metrics": deepcopy(study.metrics),
    })
    manager.store.replace_entity(
        f"Started refinement history for {study.name}",
        manager.store.project.id, "studies", candidate,
    )
    manager.select_job(job.id)
    runner = MeshConvergenceRunner(
        deepcopy(manager.store.project), candidate, analysis.id, adapter,
        str(config.get("executable", "")),
        str(config.get("arguments", config.get("extra_arguments", ""))),
        directory, manager, deck_profile=profile,
    )
    manager._runners[job.id] = runner
    runner.output.connect(
        lambda message, jid=job.id: run_for_entity(
            manager, jid, manager._study_output, jid, message
        )
    )
    runner.progress.connect(
        lambda value, label, jid=job.id: run_for_entity(
            manager, jid, manager._update_progress, jid, value, label
        )
    )
    runner.sample_ready.connect(
        lambda sample, jid=job.id, sid=study.id: run_for_entity(
            manager, jid, record_sample, manager, jid, sid, sample
        )
    )
    runner.finished.connect(
        lambda status, message, jid=job.id, sid=study.id: run_for_entity(
            manager, jid, finish_convergence, manager, jid, sid, status, message
        )
    )
    manager._start_job(job.id, "Mesh Convergence")
    runner.start()


def _history_record(study, job_id):
    return next(
        (item for item in study.run_history if item.get("job_id") == job_id),
        None,
    )


def record_sample(manager, job_id, study_id, sample):
    study = manager.store.project.try_resolve(study_id)
    if not isinstance(study, MeshConvergenceStudy):
        return
    candidate = deepcopy(study)
    record = _history_record(candidate, job_id)
    if record is None:
        return
    record["samples"].append(dict(sample))
    manager.store.replace_entity(
        f"Saved convergence level {sample['level']}",
        manager.store.project.id, "studies", candidate,
    )
    manager._update_progress(
        job_id,
        len(record["samples"]) / max(len(candidate.mesh_scales), 1),
        f"Completed mesh level {sample['level']}",
    )


def finish_convergence(manager, job_id, study_id, status, message):
    manager._runners.pop(job_id, None)
    job = manager.store.project.try_resolve(job_id)
    study = manager.store.project.try_resolve(study_id)
    if not isinstance(job, Job):
        return
    final = JobStatus.coerce(status)
    if isinstance(study, MeshConvergenceStudy):
        candidate = deepcopy(study)
        record = _history_record(candidate, job_id)
        if record is not None:
            record["status"] = final.value
            record["finished_at"] = utc_now()
            record["metric_diagnostics"] = assess_all_metrics(
                record["samples"], candidate.relative_tolerance
            )
            record["diagnostic"] = assess_convergence(
                record["samples"], candidate.relative_tolerance, candidate.metric
            )
            if message:
                record["message"] = str(message)
            manager.store.replace_entity(
                f"Finished convergence Study {candidate.name}",
                manager.store.project.id, "studies", candidate,
            )
            study = manager.store.project.resolve(candidate.id)
    candidate_job = deepcopy(job)
    candidate_job.status = final
    candidate_job.exit_code = 0 if final is JobStatus.COMPLETED else (
        130 if final is JobStatus.CANCELLED else 1
    )
    candidate_job.finished_at = utc_now()
    candidate_job.progress = 1.0 if final is JobStatus.COMPLETED else job.progress
    candidate_job.progress_label = final.value
    manager._replace_job(candidate_job, f"Finished {job.name}")
    if message:
        manager._study_output(job_id, message)
    if isinstance(study, MeshConvergenceStudy):
        record = _history_record(study, job_id)
        if record is not None and record["samples"]:
            result = ResultSet(
                name=f"{study.name} — Mesh Convergence",
                job_ref=EntityRef.of(job, "Job"),
                source_file="",
                status=ResultStatus.AVAILABLE,
                metadata={
                    "result_kind": "mesh_convergence",
                    "study_id": study.id,
                    "job_id": job_id,
                    "samples": deepcopy(record["samples"]),
                    "metric_diagnostics": deepcopy(record.get("metric_diagnostics", {})),
                    "diagnostic": record.get("diagnostic", ""),
                },
            )
            persist_result(manager.store, job_id, result)
    manager.progress_changed.emit(
        job_id, candidate_job.progress, candidate_job.progress_label
    )
    manager.parent.refresh_action_states()
