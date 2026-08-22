"""Creates, executes, monitors and persists all Analysis and Study jobs."""

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
from opencae.model.naming import next_name_from_names
from opencae.model.validation import validate_project
from opencae.optimization import TopologyOptimizationRunner, validate_topology_optimization
from opencae.results import FrdLoader
from opencae.ui.monitors import AnalysisJobMonitor, TopologyJobMonitor


class JobManager(QObject):
    """Central runtime authority for Analysis and Study executions."""

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
        self._outputs: dict[str, str] = {}
        self._runners: dict[str, object] = {}
        self._monitors: dict[str, object] = {}
        self._results = FrdLoader()
        store.changed.connect(self._repair_selection)
        self._repair_selection()

    def jobs(self):
        return tuple(self.store.project.jobs)

    def selected_job(self):
        value = self.store.project.try_resolve(self.selected_job_id)
        return value if isinstance(value, Job) else None

    def select_job(self, job_id):
        value = self.store.project.try_resolve(str(job_id or ""))
        self.selected_job_id = value.id if isinstance(value, Job) else ""
        if value is not None:
            self.store.select(value)
        self.selection_changed.emit(self.selected_job_id)
        self.output_changed.emit(
            self.selected_job_id,
            self.output_for(self.selected_job_id),
        )
        self.parent.refresh_action_states()

    def _repair_selection(self, *_):
        current = self.store.project.try_resolve(self.selected_job_id)
        if not isinstance(current, Job):
            self.selected_job_id = (
                self.store.project.jobs[-1].id
                if self.store.project.jobs
                else ""
            )

    def output_for(self, job_id):
        job_id = str(job_id or "")
        if job_id in self._outputs:
            return self._outputs[job_id]
        job = self.store.project.try_resolve(job_id)
        path = Path(getattr(job, "output_file", "")) if job else None
        if path and path.is_file():
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = ""
            self._outputs[job_id] = text[-2_000_000:]
            return self._outputs[job_id]
        return ""

    def can_stop_selected(self):
        return self.selected_job_id in self._runners

    def can_monitor_selected(self):
        return isinstance(self.selected_job(), Job)

    def can_open_selected_results(self):
        job = self.selected_job()
        return bool(
            job
            and any(
                self.store.project.try_resolve(reference) is not None
                for reference in job.result_refs
            )
        )

    def run_analysis(self, analysis_id):
        project = self.store.project
        analysis = project.try_resolve(analysis_id)
        if not isinstance(analysis, Analysis):
            self.store.message.emit("The selected Analysis no longer exists")
            return
        errors = self.validate_analysis(analysis.id, show=False)
        if errors:
            QMessageBox.warning(
                self.parent,
                "Analysis validation",
                "\n".join(f"• {item}" for item in errors),
            )
            return
        adapter = self.solvers.get(analysis.solver)
        if adapter is None:
            self.store.message.emit(
                f"Solver adapter '{analysis.solver}' is unavailable"
            )
            return
        config = self.settings.solver_config(analysis.solver)
        executable = str(config.get("executable", ""))
        directory = self._job_directory("analysis", analysis.name)
        job = self._new_job(
            analysis,
            "analysis",
            analysis.solver,
            directory,
        )
        self.store.add_entity(
            f"Created job {job.name}",
            project.id,
            "jobs",
            job,
        )
        job = self.store.project.resolve(job.id)
        self.select_job(job.id)
        runner = AnalysisJobRunner(
            deepcopy(self.store.project),
            analysis.id,
            adapter,
            executable,
            str(config.get("arguments", "")),
            directory,
            self,
        )
        self._runners[job.id] = runner
        runner.output.connect(
            lambda text, current=job.id: self._append_output(current, text)
        )
        runner.progress.connect(
            lambda value, label, current=job.id: self._update_progress(
                current,
                value,
                label,
            )
        )
        runner.finished.connect(
            lambda output_base, code, current=job.id, selected=adapter: self._analysis_finished(
                current,
                selected,
                output_base,
                code,
            )
        )
        self._start_job(job.id, "Starting Analysis")
        runner.start()

    def run_study(self, study_id):
        project = self.store.project
        study = project.try_resolve(study_id)
        if not isinstance(study, TopologyOptimization):
            self.store.message.emit("The selected Study type is not executable")
            return
        errors, _index, _masks, _operators = validate_topology_optimization(
            project,
            study,
            build_operators=False,
        )
        if errors:
            QMessageBox.warning(
                self.parent,
                "Study validation",
                "\n".join(f"• {item}" for item in errors),
            )
            return
        adapter = self.solvers.get("FEMaster")
        config = self.settings.solver_config("FEMaster")
        executable = str(config.get("executable", ""))
        directory = self._job_directory("study", study.name)
        job = self._new_job(study, "study", "FEMaster", directory)
        self.store.add_entity(
            f"Created job {job.name}",
            project.id,
            "jobs",
            job,
        )
        job = self.store.project.resolve(job.id)
        run = OptimizationRun(
            name=job.name,
            job_ref=EntityRef.of(job, "Job"),
            status="Prepared",
            directory=str(directory),
        )
        self.store.add_entity(
            f"Prepared topology state for {job.name}",
            study.id,
            "runs",
            run,
        )
        run = self.store.project.resolve(run.id)
        self.select_job(job.id)
        runner = TopologyOptimizationRunner(
            self.store,
            deepcopy(self.store.project),
            study.id,
            run.id,
            adapter,
            executable,
            str(config.get("arguments", "")),
            directory,
            self,
        )
        self._runners[job.id] = runner
        runner.progress.connect(
            lambda text, current=job.id: self._study_output(current, text)
        )
        runner.iteration_ready.connect(
            lambda run_id, iteration_id, mesh_index, density, current=job.id: self._study_iteration(
                current,
                run_id,
                iteration_id,
                mesh_index,
                density,
            )
        )
        runner.finished.connect(
            lambda status, message, current=job.id, run_id=run.id: self._study_finished(
                current,
                run_id,
                status,
                message,
            )
        )
        self._start_job(job.id, "Initializing Study")
        runner.start()

    def validate_analysis(self, analysis_id, *, show=True):
        project = self.store.project
        analysis = project.try_resolve(analysis_id)
        errors = []
        if not isinstance(analysis, Analysis):
            errors.append("Select an Analysis")
        else:
            steps = analysis.resolved_steps(project)
            if not steps:
                errors.append("The Analysis does not reference any Steps")
            errors.extend(validate_project(project, analysis=analysis))
            if analysis.solver not in self.solvers:
                errors.append(
                    f"Solver adapter '{analysis.solver}' is unavailable"
                )
            elif analysis.solver not in self.settings.enabled_solvers():
                errors.append(f"Solver '{analysis.solver}' is disabled")
            executable = str(
                self.settings.solver_config(analysis.solver).get(
                    "executable",
                    "",
                )
            )
            if not Path(executable).is_file():
                errors.append(
                    f"Solver executable is unavailable: {executable or '<not configured>'}"
                )
        errors = list(dict.fromkeys(errors))
        if show:
            if errors:
                QMessageBox.warning(
                    self.parent,
                    "Analysis validation",
                    "\n".join(f"• {item}" for item in errors),
                )
            else:
                QMessageBox.information(
                    self.parent,
                    "Analysis validation",
                    "The active Analysis is valid.",
                )
        return errors

    def validate_study(self, study_id, *, show=True):
        study = self.store.project.try_resolve(study_id)
        if isinstance(study, TopologyOptimization):
            errors, *_ = validate_topology_optimization(
                self.store.project,
                study,
                build_operators=False,
            )
        else:
            errors = ["Select an executable Study"]
        if show:
            if errors:
                QMessageBox.warning(
                    self.parent,
                    "Study validation",
                    "\n".join(f"• {item}" for item in errors),
                )
            else:
                QMessageBox.information(
                    self.parent,
                    "Study validation",
                    "The active Study is valid.",
                )
        return errors

    def stop_selected(self):
        runner = self._runners.get(self.selected_job_id)
        if runner is None:
            return
        runner.stop()

    def open_selected_monitor(self):
        job = self.selected_job()
        if job is None:
            return
        existing = self._monitors.get(job.id)
        if existing is not None:
            existing.show()
            existing.raise_()
            existing.activateWindow()
            return
        if job.source_kind == "study":
            monitor = TopologyJobMonitor(self.store, job.id, self.parent)
            self.topology_frame.connect(monitor.show_frame)
        else:
            monitor = AnalysisJobMonitor(self.store, job.id, self.parent)
        self.progress_changed.connect(monitor.set_progress)
        monitor.destroyed.connect(
            lambda _value=None, current=job.id: self._monitors.pop(
                current,
                None,
            )
        )
        self._monitors[job.id] = monitor
        monitor.show()

    def open_selected_results(self):
        job = self.selected_job()
        if job is None:
            return
        result = next(
            (
                self.store.project.try_resolve(reference)
                for reference in job.result_refs
                if self.store.project.try_resolve(reference) is not None
            ),
            None,
        )
        if result is None:
            self.store.message.emit("The selected Job has no available Results")
            return
        self.parent.show_solution(result)

    def _start_job(self, job_id, label):
        job = self.store.project.resolve(job_id)
        candidate = deepcopy(job)
        candidate.status = "Running"
        candidate.started_at = _now()
        candidate.progress = 0.0
        candidate.progress_label = label
        self._replace_job(candidate, f"Started {job.name}")
        self._append_output(job.id, f"{label}\n")
        self.progress_changed.emit(job.id, 0.0, label)

    def _job_directory(self, source_kind, source_name):
        project = self.store.project
        root = (
            project.path.parent / f"{project.path.stem}_data"
            if project.path
            else Path.cwd() / ".opencae"
        )
        name = next_name_from_names(
            f"{source_name} Job",
            [job.name for job in project.jobs],
        )
        directory = root / "jobs" / name.replace(" ", "-")
        counter = 2
        while directory.exists():
            directory = root / "jobs" / f"{name.replace(' ', '-')}-{counter}"
            counter += 1
        return directory

    def _new_job(self, source, source_kind, solver, directory):
        directory.mkdir(parents=True, exist_ok=True)
        name = next_name_from_names(
            f"{source.name} Job",
            [job.name for job in self.store.project.jobs],
        )
        job = Job(
            name=name,
            source_ref=EntityRef.of(source, type(source).__name__),
            source_kind=source_kind,
            solver=solver,
            status="Prepared",
            created_at=_now(),
        )
        job.directory = str(directory)
        job.output_file = str(directory / "output.log")
        return job

    def _append_output(self, job_id, text):
        job_id = str(job_id)
        addition = str(text)
        value = self._outputs.get(job_id, "") + addition
        self._outputs[job_id] = value[-2_000_000:]
        job = self.store.project.try_resolve(job_id)
        output_path = Path(getattr(job, "output_file", "")) if job else None
        if output_path:
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with output_path.open("a", encoding="utf-8") as stream:
                    stream.write(addition)
            except OSError:
                pass
        if job_id == self.selected_job_id:
            self.output_changed.emit(job_id, self._outputs[job_id])

    def _study_output(self, job_id, text):
        line = str(text)
        self._append_output(
            job_id,
            line + ("" if line.endswith("\n") else "\n"),
        )

    def _update_progress(self, job_id, progress, label):
        job = self.store.project.try_resolve(job_id)
        if not isinstance(job, Job):
            return
        candidate = deepcopy(job)
        candidate.progress = min(max(float(progress), 0.0), 1.0)
        candidate.progress_label = str(label)
        self._replace_job(candidate, f"Updated {job.name} progress")
        self.progress_changed.emit(
            job.id,
            candidate.progress,
            candidate.progress_label,
        )

    def _analysis_finished(self, job_id, adapter, output_base, code):
        self._runners.pop(job_id, None)
        job = self.store.project.try_resolve(job_id)
        if not isinstance(job, Job):
            return
        completed = int(code) == 0
        candidate = deepcopy(job)
        candidate.status = (
            "Completed"
            if completed
            else "Cancelled"
            if int(code) == 130
            else f"Failed ({int(code)})"
        )
        candidate.finished_at = _now()
        candidate.progress = 1.0 if completed else candidate.progress
        candidate.progress_label = candidate.status
        self._replace_job(candidate, f"Finished {job.name}")

        source = next(
            (
                path
                for path in adapter.result_candidates(Path(output_base))
                if path.exists()
            ),
            None,
        )
        if completed and source and source.suffix.lower() == ".frd":
            try:
                fields = self._results.fields(source)
            except Exception as exc:
                fields = []
                self._append_output(
                    job.id,
                    f"Result metadata failed: {exc}\n",
                )
            analysis = self.store.project.try_resolve(job.source_ref)
            steps = (
                analysis.resolved_steps(self.store.project)
                if isinstance(analysis, Analysis)
                else ()
            )
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
        self.progress_changed.emit(
            job.id,
            candidate.progress,
            candidate.progress_label,
        )
        self.parent.refresh_action_states()

    def _study_iteration(
        self,
        job_id,
        run_id,
        iteration_id,
        mesh_index,
        density,
    ):
        run = self.store.project.try_resolve(run_id)
        iteration = self.store.project.try_resolve(iteration_id)
        job = self.store.project.try_resolve(job_id)
        study = (
            self.store.project.try_resolve(job.source_ref)
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
        self._update_progress(job.id, progress, label)
        self.topology_frame.emit(
            job.id,
            run,
            iteration,
            mesh_index,
            np.asarray(density, dtype=float).copy(),
        )

    def _study_finished(self, job_id, run_id, status, message=""):
        self._runners.pop(job_id, None)
        job = self.store.project.try_resolve(job_id)
        run = self.store.project.try_resolve(run_id)
        if not isinstance(job, Job):
            return
        if message:
            self._study_output(job.id, message)
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
                    "study_ref": (
                        job.source_ref.entity_id if job.source_ref else ""
                    ),
                    "run_ref": run.id,
                    "mesh_fingerprint": run.mesh_fingerprint,
                    "frames": frames,
                },
            )
            self._add_result(job.id, result)
        self.progress_changed.emit(
            job.id,
            candidate.progress,
            candidate.progress_label,
        )
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
            result_id = result.id
            self.store.add_entity(
                f"Added results for {result.name}",
                project.id,
                "results",
                result,
            )
        else:
            replacement = deepcopy(previous)
            replacement.name = result.name
            replacement.job_ref = result.job_ref
            replacement.source_file = result.source_file
            replacement.status = result.status
            replacement.fields = deepcopy(result.fields)
            replacement.metadata = deepcopy(result.metadata)
            result_id = replacement.id
            self.store.replace_entity(
                f"Updated results for {result.name}",
                project.id,
                "results",
                replacement,
            )
        current_job = self.store.project.try_resolve(job_id)
        current_result = self.store.project.try_resolve(result_id)
        if isinstance(current_job, Job) and current_result is not None:
            candidate = deepcopy(current_job)
            candidate.result_refs = [
                EntityRef.of(current_result, "ResultSet")
            ]
            self._replace_job(
                candidate,
                f"Linked results to {current_job.name}",
            )

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
