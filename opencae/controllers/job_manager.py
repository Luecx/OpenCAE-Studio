"""Coordinates the Qt-facing lifecycle of Analysis and Study Jobs.

JobManager intentionally owns only selection, signals, monitor lifecycle, and
small mutation boundaries. Solver preparation, validation, output I/O, result
persistence, and Analysis/Study workflows live in focused companion modules.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import fields

from PyQt6.QtCore import QCoreApplication, QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

from opencae.model.entities.jobs import Job, JobSourceKind, JobStatus
from opencae.results import FrdLoader
from opencae.ui.monitors import AnalysisJobMonitor, TopologyJobMonitor

from .job_manager_analysis import run_analysis as run_analysis_workflow
from .job_manager_factory import utc_now
from .job_manager_study import run_study as run_study_workflow
from .job_manager_validation import analysis_errors, study_errors
from .job_output_store import JobOutputStore


_RUNTIME_JOB_FIELDS = frozenset({
    "status",
    "exit_code",
    "started_at",
    "finished_at",
    "progress",
    "progress_label",
})


class JobManager(QObject):
    """Qt orchestrator for Job selection, runners, progress, output, and monitors."""

    selection_changed = pyqtSignal(str)
    output_appended = pyqtSignal(str, str)
    progress_changed = pyqtSignal(str, float, str)
    topology_frame = pyqtSignal(str, object, object, object, object)

    def __init__(self, store, parent, settings, solvers):
        """Bind the manager to the live project store and runtime services."""
        super().__init__(parent)
        self.store = store
        self.parent = parent
        self.settings = settings
        self.solvers = solvers
        self.selected_job_id = ""
        self._runners: dict[str, object] = {}
        self._monitors: dict[str, object] = {}
        self._output_store = JobOutputStore(lambda: self.store.project)
        self._result_loader = FrdLoader()
        self._pending_output: dict[str, list[str]] = {}
        self._pending_output_chars: dict[str, int] = {}
        self._output_flush_timer = QTimer(self)
        self._output_flush_timer.setSingleShot(True)
        self._output_flush_timer.setInterval(40)
        self._output_flush_timer.timeout.connect(self._flush_pending_output)
        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._flush_pending_output)
        store.changed.connect(self._repair_selection)
        self._repair_selection()

    def jobs(self) -> tuple[Job, ...]:
        """Return the project Jobs in persistent display order."""
        return tuple(self.store.project.jobs)

    def selected_job(self) -> Job | None:
        """Resolve and return the currently selected Job, if it still exists."""
        value = self.store.project.try_resolve(self.selected_job_id)
        return value if isinstance(value, Job) else None

    def select_job(self, job_id) -> None:
        """Synchronize Job selection across store, panels, and actions."""
        value = self.store.project.try_resolve(str(job_id or ""))
        self.selected_job_id = value.id if isinstance(value, Job) else ""
        if value is not None:
            self.store.select(value)
        self.selection_changed.emit(self.selected_job_id)
        # Selecting a row no longer owns any output presentation. Solver text is
        # loaded only when a dedicated monitor is opened.
        self.parent.refresh_action_states()

    def _repair_selection(self, *_args) -> None:
        """Keep selection valid after project mutations or undo/redo."""
        current = self.store.project.try_resolve(self.selected_job_id)
        if isinstance(current, Job):
            return
        self.selected_job_id = (
            self.store.project.jobs[-1].id if self.store.project.jobs else ""
        )

    def output_for(self, job_id) -> str:
        """Return the bounded persisted solver output for one Job."""
        key = str(job_id or "")
        self._flush_pending_output(key)
        return self._output_store.read(key)

    def can_stop_selected(self) -> bool:
        """Return whether the selected Job still has a live runner."""
        return self.selected_job_id in self._runners

    def can_monitor_selected(self) -> bool:
        """Return whether a persistent Job is selected."""
        return isinstance(self.selected_job(), Job)

    def can_open_selected_results(self) -> bool:
        """Return whether the selected Job references an available ResultSet."""
        job = self.selected_job()
        return bool(
            job
            and any(
                self.store.project.try_resolve(reference) is not None
                for reference in job.result_refs
            )
        )

    def run_analysis(self, analysis_id) -> None:
        """Start one Analysis through the focused Analysis Job workflow."""
        run_analysis_workflow(self, analysis_id)

    def run_study(self, study_id) -> None:
        """Start one executable Study through the focused Study Job workflow."""
        run_study_workflow(self, study_id)

    def validate_analysis(self, analysis_id, *, show: bool = True) -> list[str]:
        """Validate one Analysis and optionally present diagnostics to the user."""
        errors = analysis_errors(
            self.store.project,
            analysis_id,
            self.settings,
            self.solvers,
        )
        if show:
            self._show_validation("Analysis", errors)
        return errors

    def validate_study(self, study_id, *, show: bool = True) -> list[str]:
        """Validate one executable Study and optionally show diagnostics."""
        errors = study_errors(self.store.project, study_id)
        if show:
            self._show_validation("Study", errors)
        return errors

    def _show_validation(self, kind: str, errors: list[str]) -> None:
        """Present one standardized validation result dialog."""
        if errors:
            QMessageBox.warning(
                self.parent,
                f"{kind} validation",
                "\n".join(f"• {item}" for item in errors),
            )
            return
        QMessageBox.information(
            self.parent,
            f"{kind} validation",
            f"The active {kind} is valid.",
        )

    def stop_selected(self) -> None:
        """Request cancellation of the selected live Job."""
        self.stop_job(self.selected_job_id)

    def stop_job(self, job_id) -> None:
        """Request cancellation of one live Job without relying on UI selection."""
        job_key = str(job_id or "")
        runner = self._runners.get(job_key)
        job = self.store.project.try_resolve(job_key)
        if runner is None or not isinstance(job, Job):
            return

        # Persist STOPPING before terminating the process so every observer sees
        # a valid intermediate state rather than inferring it from a button click.
        candidate = deepcopy(job)
        candidate.status = JobStatus.STOPPING
        candidate.progress_label = JobStatus.STOPPING.value
        self._replace_job(candidate, f"Stopping {job.name}")
        self.progress_changed.emit(
            job.id,
            candidate.progress,
            candidate.progress_label,
        )
        runner.stop()

    def open_selected_monitor(self) -> None:
        """Open or focus the monitor appropriate for the selected Job source."""
        job = self.selected_job()
        if job is None:
            return
        existing = self._monitors.get(job.id)
        if existing is not None:
            existing.show()
            existing.raise_()
            existing.activateWindow()
            return

        if job.source_kind is JobSourceKind.STUDY:
            monitor = TopologyJobMonitor(self.store, job.id, self.parent)
            self.topology_frame.connect(monitor.show_frame)
        else:
            stop_callback = (
                (lambda current=job.id: self.stop_job(current))
                if job.id in self._runners
                else None
            )
            monitor = AnalysisJobMonitor(
                self.store,
                job.id,
                self.parent,
                stop_callback=stop_callback,
            )

        self.progress_changed.connect(monitor.set_progress)
        self.output_appended.connect(monitor.append_output)
        monitor.set_output(job.id, self.output_for(job.id))
        monitor.destroyed.connect(
            lambda _value=None, current=job.id: self._monitors.pop(current, None)
        )
        self._monitors[job.id] = monitor
        monitor.show()

    def open_selected_results(self) -> None:
        """Show the first resolvable ResultSet linked to the selected Job."""
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

    def _start_job(self, job_id, label: str) -> None:
        """Move a prepared Job into the canonical RUNNING state."""
        job = self.store.project.resolve(job_id)
        candidate = deepcopy(job)
        candidate.status = JobStatus.RUNNING
        candidate.exit_code = None
        candidate.started_at = utc_now()
        candidate.progress = 0.0
        candidate.progress_label = str(label)
        self._replace_job(candidate, f"Started {job.name}")
        self._append_output(job.id, f"{label}\n")
        self.progress_changed.emit(job.id, 0.0, str(label))

    def _append_output(self, job_id, text) -> None:
        """Buffer solver output so high-volume stdout cannot starve Qt's event loop."""
        job_key = str(job_id)
        addition = str(text)
        if not addition:
            return
        self._pending_output.setdefault(job_key, []).append(addition)
        size = self._pending_output_chars.get(job_key, 0) + len(addition)
        self._pending_output_chars[job_key] = size

        # Flush at most roughly 25 times/s during ordinary streaming. Very large
        # chunks are committed immediately to keep transient memory bounded.
        if size >= 64 * 1024:
            self._flush_pending_output(job_key)
        elif not self._output_flush_timer.isActive():
            self._output_flush_timer.start()

    def _flush_pending_output(self, job_id=None) -> None:
        """Persist and publish buffered output in coarse GUI-friendly chunks."""
        keys = (
            (str(job_id),)
            if job_id is not None
            else tuple(self._pending_output)
        )
        for key in keys:
            parts = self._pending_output.pop(key, None)
            self._pending_output_chars.pop(key, None)
            if not parts:
                continue
            addition = "".join(parts)
            self._output_store.append(key, addition)
            # Monitors can remain open while another Job is selected, so each
            # event carries its Job id and the monitor performs final filtering.
            self.output_appended.emit(key, addition)

        if self._pending_output and not self._output_flush_timer.isActive():
            self._output_flush_timer.start()

    def _study_output(self, job_id, text) -> None:
        """Normalize Study output chunks before buffered persistence."""
        chunk = str(text)
        self._append_output(
            job_id,
            chunk + ("" if chunk.endswith("\n") else "\n"),
        )

    def _update_progress(self, job_id, progress, label) -> None:
        """Persist normalized Job progress and emit the shared progress signal."""
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

    def _replace_job(self, candidate: Job, description: str) -> None:
        """Apply only scalar Job runtime fields without a full Project transaction."""
        current = self.store.project.try_resolve(candidate.id)
        if not isinstance(current, Job):
            return

        # This hot path is deliberately incapable of changing relationships,
        # identity, paths or settings. Those remain ordinary document edits and
        # must use ProjectStore.replace_entity()/execute(). Runtime-only fields
        # such as Entity._project are detached by deepcopy and are intentionally
        # excluded from this persistent-state guard.
        for field_info in fields(current):
            name = field_info.name
            if (
                name in _RUNTIME_JOB_FIELDS
                or field_info.metadata.get("serialize", True) is False
            ):
                continue
            if getattr(current, name) != getattr(candidate, name):
                raise ValueError(
                    f"Job runtime update attempted to change non-runtime field '{name}'"
                )

        changes = {
            name: getattr(candidate, name)
            for name in _RUNTIME_JOB_FIELDS
            if getattr(current, name) != getattr(candidate, name)
        }
        self.store.update_runtime_fields(current.id, changes)
