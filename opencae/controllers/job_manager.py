"""Coordinates all Analysis and Study jobs, output, monitors and results."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

from opencae.jobs import AnalysisJobRunner
from opencae.model.core import EntityRef
from opencae.model.entities.analysis import Analysis
from opencae.model.entities.jobs import Job, ResultSet
from opencae.model.entities.optimization import OptimizationRun, TopologyOptimization
from opencae.optimization import build_mesh_index, validate_topology_optimization
from opencae.optimization.runner import TopologyOptimizationRunner
from opencae.results import FrdLoader


class JobManager(QObject):
    """Single runtime authority for creating, controlling and presenting jobs."""

    selection_changed = pyqtSignal(str)
    output_changed = pyqtSignal(str, str)
    progress_changed = pyqtSignal(str, float, str)
    topology_frame = pyqtSignal(str, object, object, object, object)

    def __init__(self, store, parent, settings, solvers):
        super().__init__(parent)
        self.store = store
        self.parent = parent
        self.settings = settings
        self.solvers = solvers
        self.selected_job_id = ""
        self._runners = {}
        self._outputs = {}
        self._monitors = {}
        self._topology_run_for_job = {}
        self._results = FrdLoader()
        store.changed.connect(self._repair_selection)

    def jobs(self):
        return tuple(self.store.project.jobs)

    def selected_job(self):
        value = self.store.project.try_resolve(self.selected_job_id)
        return value if isinstance(value, Job) else None

    def select_job(self, job_id):
        value = self.store.project.try_resolve(str(job_id or ""))
        self.selected_job_id = value.id if isinstance(value, Job) else ""
        self.selection_changed.emit(self.selected_job_id)
        if value is not None:
            self.output_changed.emit(value.id, self.output_for(value.id))
        self.parent.refresh_action_states()

    def _repair_selection(self, *_):
        if self.store.project.try_resolve(self.selected_job_id) is None:
            self.selected_job_id = (
                self.store.project.jobs[-1].id
                if self.store.project.jobs
                else ""
            )
            self.selection_changed.emit(self.selected_job_id)

    def output_for(self, job_id):
        job_id = str(job_id or "")
        if job_id in self._outputs:
            return self._outputs[job_id]
        job = self.store.project.try_resolve(job_id)
        path = Path(job.output_file) if isinstance(job, Job) and job.output_file else None
        if path is not None and path.exists():
            try:
                return path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass
        return ""

    def validate_analysis(self, analysis_id):
        try:
            analysis, adapter, _config, deck = self._analysis_inputs(analysis_id)
        except Exception as exc:
            QMessageBox.warning(self.parent, "Analysis validation failed", str(exc))
            return False
        self.store.message.emit(
            f"Analysis {analysis.name} is valid for {adapter.name} "
            f"({len(deck.splitlines())} deck lines)"
        )
        return True

    def run_analysis(self, analysis_id):
        try:
            analysis, adapter, config, deck = self._analysis_inputs(analysis_id)
        except Exception as exc:
            QMessageBox.warning(self.parent, "Analysis cannot start", str(exc))
            return
        executable = str(config.get("executable", ""))
        if not Path(executable).is_file():
            QMessageBox.warning(
                self.parent,
                "Solver unavailable",
                f"Configure a valid {adapter.name} executable first.",
            )
            return

        job = self._new_job(analysis, "analysis", adapter.name)
        directory = Path(job.directory)
        deck_path = directory / f"{job.name}.inp"
        output_base = directory / job.name
        deck_path.write_text(deck, encoding="utf-8")
        job.input_deck = str(deck_path)
        self.store.add_entity(
            f"Started {job.name}",
            self.store.project.id,
            "jobs",
            job,
        )

        extra = str(config.get("extra_arguments", ""))
        threads = int(config.get("threads", 0) or 0)
        if adapter.name == "FEMaster" and threads > 0:
            extra = f"--ncpus {threads} {extra}".strip()
        command = adapter.build_command(executable, deck_path, output_base, extra)
        runner = AnalysisJobRunner(
            job.id,
            command,
            directory,
            output_base,
            job.output_file,
            self.parent,
        )
        runner.output.connect(self._append_output)
        runner.progress.connect(self._update_progress)
        runner.finished.connect(
            lambda jid, code, base, value=adapter: self._analysis_finished(
                jid,
                value,
                base,
                code,
            )
        )
        self._runners[job.id] = runner
        self.select_job(job.id)
        self._append_output(
            job.id,
            f"{job.name} — {analysis.name} — {adapter.name}\n",
        )
        runner.start()

    def run_study(self, study_id):
        study = self.store.project.try_resolve(study_id)
        if not isinstance(study, TopologyOptimization):
            self.store.message.emit("The selected Study type has no runner")
            return
        adapter = self.solvers.get("FEMaster")
        config = self.settings.solver_config("FEMaster")
        executable = str(config.get("executable", ""))
        if adapter is None or not Path(executable).is_file():
            QMessageBox.warning(
                self.parent,
                "FEMaster unavailable",
                "Configure a valid FEMaster executable before running this Study.",
            )
            return
        errors, _index, _masks, _operators = validate_topology_optimization(
            self.store.project,
            study,
            build_operators=True,
        )
        if errors:
            QMessageBox.warning(
                self.parent,
                "Study validation failed",
                "\n".join(f"• {item}" for item in errors),
            )
            return

        job = self._new_job(study, "study", adapter.name)
        run = OptimizationRun(
            name=f"Topology State-{len(study.runs) + 1}",
            optimization_ref=EntityRef.of(study, "TopologyOptimization"),
            job_ref=EntityRef.of(job, "Job"),
            status="Prepared",
            directory=job.directory,
        )
        self.store.add_entity(
            f"Started {job.name}",
            self.store.project.id,
            "jobs",
            job,
        )
        self.store.add_entity(
            f"Created topology state for {job.name}",
            study.id,
            "runs",
            run,
        )
        self._topology_run_for_job[job.id] = run.id

        runner = TopologyOptimizationRunner(
            self.store,
            deepcopy(self.store.project),
            study.id,
            run.id,
            adapter,
            executable,
            str(config.get("extra_arguments", "")),
            job.directory,
            self.parent,
        )
        runner.progress.connect(
            lambda text, jid=job.id: self._study_output(jid, text)
        )
        runner.iteration_ready.connect(
            lambda rid, iid, index, density, jid=job.id: self._study_iteration(
                jid,
                rid,
                iid,
                index,
                density,
            )
        )
        runner.finished.connect(
            lambda rid, status, jid=job.id: self._study_finished(
                jid,
                rid,
                status,
            )
        )
        self._runners[job.id] = runner
        self.select_job(job.id)
        self._append_output(job.id, f"{job.name} — {study.name}\n")
        try:
            self.parent.ribbon.set_stage("STUDIES")
        except AttributeError:
            pass
        runner.start()

    def stop_selected(self):
        self.stop(self.selected_job_id)

    def stop(self, job_id):
        job = self.store.project.try_resolve(job_id)
        runner = self._runners.get(str(job_id or ""))
        if not isinstance(job, Job) or runner is None:
            self.store.message.emit("The selected job is not running")
            return
        candidate = deepcopy(job)
        candidate.status = "Stopping"
        candidate.progress_label = "Stopping"
        self._replace_job(candidate, f"Stopping {job.name}")
        runner.stop()

    def monitor_selected(self):
        self.open_monitor(self.selected_job_id)

    def open_monitor(self, job_id):
        job = self.store.project.try_resolve(job_id)
        if not isinstance(job, Job):
            return
        existing = self._monitors.get(job.id)
        if existing is not None:
            existing.show()
            existing.raise_()
            existing.activateWindow()
            return
        if job.source_kind == "study":
            from opencae.ui.monitors.topology_job_monitor import TopologyJobMonitor

            monitor = TopologyJobMonitor(self.store, job.id, self.parent)
            self.topology_frame.connect(monitor.show_frame)
        else:
            from opencae.ui.monitors.analysis_job_monitor import AnalysisJobMonitor

            monitor = AnalysisJobMonitor(self.store, job.id, self.parent)
        self.progress_changed.connect(monitor.set_progress)
        monitor.finished.connect(
            lambda _code, jid=job.id: self._monitors.pop(jid, None)
        )
        self._monitors[job.id] = monitor
        monitor.show()
        monitor.set_progress(job.id, job.progress, job.progress_label)

    def open_selected_results(self):
        self.open_results(self.selected_job_id)

    def open_results(self, job_id):
        result = next(
            (
                item
                for item in self.store.project.results
                if item.job_ref and item.job_ref.entity_id == str(job_id or "")
            ),
            None,
        )
        if result is None:
            self.store.message.emit("The selected job has no available results")
            return
        self.parent.show_solution(result)

    def can_stop_selected(self):
        return self.selected_job_id in self._runners

    def can_monitor_selected(self):
        return self.selected_job() is not None

    def can_open_selected_results(self):
        return any(
            item.job_ref and item.job_ref.entity_id == self.selected_job_id
            for item in self.store.project.results
        )

    def _analysis_inputs(self, analysis_id):
        project = self.store.project
        analysis = project.try_resolve(analysis_id)
        if not isinstance(analysis, Analysis):
            raise ValueError("Select an Analysis first")
        steps = analysis.resolved_steps(project)
        if not steps:
            raise ValueError("The Analysis references no existing Steps")
        if not any(not item.suppressed for item in project.assembly.instances):
            raise ValueError("Create at least one active assembly instance")
        adapter = self.solvers.get(analysis.solver)
        if adapter is None:
            raise ValueError(f"The Analysis solver {analysis.solver!r} is disabled")
        config = self.settings.solver_config(analysis.solver)
        deck = adapter.write_deck_text(project, analysis)
        return analysis, adapter, config, deck

    def _new_job(self, source, source_kind, solver):
        number = len(self.store.project.jobs) + 1
        job = Job(
            name=f"Job-{number}",
            source_ref=EntityRef.of(source, type(source).__name__),
            source_kind=source_kind,
            solver=solver,
            status="Running",
            created_at=_now(),
            started_at=_now(),
            progress=0.01,
            progress_label="Starting",
        )
        root = Path(
            self.settings.working_directory
            or (
                self.store.project.path.parent
                if self.store.project.path
                else Path.cwd()
            )
        )
        safe = "".join(
            value if value.isalnum() or value in "-_" else "_"
            for value in source.name
        )
        directory = root / f"{safe}-{job.id[-8:]}"
        directory.mkdir(parents=True, exist_ok=True)
        job.directory = str(directory)
        job.output_file = str(directory / "output.log")
        return job

    def _append_output(self, job_id, text):
        job_id = str(job_id)
        value = self._outputs.get(job_id, "") + str(text)
        self._outputs[job_id] = value[-2_000_000:]
        if job_id == self.selected_job_id:
            self.output_changed.emit(job_id, self._outputs[job_id])

    def _study_output(self, job_id, text):
        line = str(text)
        self._append_output(job_id, line + ("" if line.endswith("\n") else "\n"))

    def _update_progress(self, job_id, progress, label):
        job = self.store.project.try_resolve(job_id)
        if not isinstance(job, Job):
            return
        candidate = deepcopy(job)
        candidate.progress = min(max(float(progress), 0.0), 1.0)
        candidate.progress_label = str(label)
        self._replace_job(candidate, f"Updated {job.name} progress")
        self.progress_changed.emit(job.id, candidate.progress, candidate.progress_label)

    def _analysis_finished(self, job_id, adapter, output_base, code):
        self._runners.pop(job_id, None)
        job = self.store.project.try_resolve(job_id)
        if not isinstance(job, Job):
            return
        completed = int(code) == 0
        candidate = deepcopy(job)
        candidate.status = "Completed" if completed else (
            "Cancelled" if int(code) == 130 else f"Failed ({int(code)})"
        )
        candidate.finished_at = _now()
        candidate.progress = 1.0 if completed else candidate.progress
        candidate.progress_label = candidate.status
        self._replace_job(candidate, f"Finished {job.name}")

        source = next(
            (path for path in adapter.result_candidates(Path(output_base)) if path.exists()),
            None,
        )
        if completed and source and source.suffix.lower() == ".frd":
            try:
                fields = self._results.fields(source)
            except Exception as exc:
                fields = []
                self._append_output(job.id, f"Result metadata failed: {exc}\n")
            analysis = self.store.project.try_resolve(job.source_ref)
            steps = analysis.resolved_steps(self.store.project) if isinstance(analysis, Analysis) else ()
            result = ResultSet(
                name=job.name,
                job_ref=EntityRef.of(job, "Job"),
                source_file=str(source),
                status="Available",
                fields=fields,
                metadata={
                    "result_kind": "solver",
                    "step_names": [step.name for step in steps],
                },
            )
            self._add_result(job.id, result)
        self.progress_changed.emit(job.id, candidate.progress, candidate.progress_label)
        self.parent.refresh_action_states()

    def _study_iteration(self, job_id, run_id, iteration_id, mesh_index, density):
        run = self.store.project.try_resolve(run_id)
        iteration = self.store.project.try_resolve(iteration_id)
        job = self.store.project.try_resolve(job_id)
        study = self.store.project.try_resolve(job.source_ref) if isinstance(job, Job) else None
        if not isinstance(job, Job) or run is None or iteration is None:
            return
        maximum = max(
            int(getattr(getattr(study, "control_settings", None), "maximum_iterations", 1)),
            1,
        )
        progress = min(float(iteration.number) / maximum, 0.99)
        label = f"Iteration {iteration.number}"
        self._update_progress(job.id, progress, label)
        self.topology_frame.emit(
            job.id,
            run,
            iteration,
            mesh_index,
            np.asarray(density, dtype=float).copy(),
        )

    def _study_finished(self, job_id, run_id, status):
        self._runners.pop(job_id, None)
        job = self.store.project.try_resolve(job_id)
        run = self.store.project.try_resolve(run_id)
        if not isinstance(job, Job):
            return
        candidate = deepcopy(job)
        candidate.status = str(status)
        candidate.finished_at = _now()
        candidate.progress = 1.0 if status == "Completed" else candidate.progress
        candidate.progress_label = str(status)
        self._replace_job(candidate, f"Finished {job.name}")

        if isinstance(run, OptimizationRun) and run.iterations:
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
                status="Available",
                metadata={
                    "result_kind": "topology_density",
                    "study_ref": job.source_ref.entity_id if job.source_ref else "",
                    "run_ref": run.id,
                    "mesh_fingerprint": run.mesh_fingerprint,
                    "frames": frames,
                },
            )
            self._add_result(job.id, result)
        self.progress_changed.emit(job.id, candidate.progress, candidate.progress_label)
        self.parent.refresh_action_states()

    def _add_result(self, job_id, result):
        project = self.store.project
        previous = next(
            (
                item
                for item in project.results
                if item.job_ref and item.job_ref.entity_id == job_id
            ),
            None,
        )
        if previous is None:
            self.store.add_entity(
                f"Added results for {result.name}",
                project.id,
                "results",
                result,
            )
        else:
            result.id = previous.id
            self.store.replace_entity(
                f"Updated results for {result.name}",
                project.id,
                "results",
                result,
            )
        current_job = self.store.project.try_resolve(job_id)
        current_result = self.store.project.try_resolve(result.id)
        if isinstance(current_job, Job) and current_result is not None:
            candidate = deepcopy(current_job)
            candidate.result_refs = [EntityRef.of(current_result, "ResultSet")]
            self._replace_job(candidate, f"Linked results to {current_job.name}")

    def _replace_job(self, candidate, description):
        if self.store.project.try_resolve(candidate.id) is None:
            return
        self.store.replace_entity(
            description,
            self.store.project.id,
            "jobs",
            candidate,
        )


def _now():
    return datetime.now(timezone.utc).isoformat()
