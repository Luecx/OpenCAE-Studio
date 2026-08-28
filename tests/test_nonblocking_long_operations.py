"""Regression coverage for keeping long-running work away from Qt's GUI thread."""

from __future__ import annotations

from pathlib import Path
from time import sleep

import pytest
from PyQt6.QtCore import QEventLoop, QThread, QTimer
from PyQt6.QtWidgets import QApplication

from opencae.controllers.background_task import BackgroundTask
from opencae.model.core import EntityRef
from opencae.model.entities.jobs import Job, JobStatus
from opencae.model.project import Project
from opencae.store.project_store import ProjectStore


ROOT = Path(__file__).resolve().parents[1]


def test_background_task_keeps_qt_event_loop_responsive_and_marshals_result():
    app = QApplication.instance() or QApplication([])
    loop = QEventLoop()
    heartbeats = []
    results = []

    heartbeat = QTimer()
    heartbeat.setInterval(5)
    heartbeat.timeout.connect(lambda: heartbeats.append(1))
    heartbeat.start()

    def slow_operation():
        sleep(0.08)
        return 42

    def completed(value):
        results.append((value, QThread.currentThread() is app.thread()))
        loop.quit()

    task = BackgroundTask(
        slow_operation,
        on_result=completed,
        parent=app,
    )
    task.start()
    QTimer.singleShot(1500, loop.quit)
    loop.exec()
    heartbeat.stop()

    # Wait only in the test teardown so the QThread cannot outlive QApplication.
    task.wait(1000)
    app.processEvents()

    assert results == [(42, True)]
    assert len(heartbeats) >= 3


def test_runtime_job_progress_does_not_copy_document_or_enter_undo_history():
    job = Job(name="Long Job")
    store = ProjectStore(Project(name="P", jobs=[job]))
    live = store.project.resolve(job.id)
    index_before = store.project.index
    undo_count = len(store._undo)
    document_events = []
    runtime_events = []
    store.changed.connect(document_events.append)
    store.runtime_changed.connect(
        lambda entity_id, names: runtime_events.append((entity_id, tuple(names)))
    )

    store.update_runtime_fields(
        live.id,
        {
            "status": JobStatus.RUNNING,
            "progress": 0.625,
            "progress_label": "Solving",
        },
    )

    assert live.status is JobStatus.RUNNING
    assert live.progress == pytest.approx(0.625)
    assert live.progress_label == "Solving"
    assert len(store._undo) == undo_count
    # Scalar lifecycle metadata changes neither ownership nor EntityRefs. Keeping
    # the exact same ProjectIndex object is the performance contract here.
    assert store.project.index is index_before
    assert document_events == []
    assert runtime_events == [
        (live.id, ("status", "progress", "progress_label"))
    ]

    with pytest.raises(TypeError):
        store.update_runtime_fields(
            live.id,
            {"source_ref": EntityRef("analysis-id")},
        )


def test_analysis_runner_never_waits_synchronously_for_solver_process():
    source = (ROOT / "opencae/jobs/analysis_job_runner.py").read_text(
        encoding="utf-8"
    )
    assert "BackgroundTask(" in source
    assert "Preparing analysis" in source
    assert "waitForFinished" not in source
    assert "QTimer.singleShot(1500, self._kill_if_running)" in source


def test_topology_runner_prepares_and_consumes_iterations_off_thread():
    source = (ROOT / "opencae/optimization/runner.py").read_text(
        encoding="utf-8"
    )
    assert source.count("BackgroundTask(") >= 2
    assert "preparing solver input" in source
    assert "processing results" in source
    assert "_compute_iteration_payload" in source
    assert "waitForFinished" not in source


def test_topology_job_adapter_uses_chunked_output_and_lightweight_runtime_commits():
    source = (ROOT / "opencae/optimization/job_runner.py").read_text(
        encoding="utf-8"
    )
    assert "self.progress.emit(text)" in source
    assert "text.splitlines()" not in source
    assert "update_runtime_fields" in source
    assert "_append_iteration_runtime" in source
    assert "index.by_id[stored.id] = stored" in source
    assert "self.store.add_entity(" not in source
    assert "self.store.replace_entity(" not in source


def test_mesh_generation_runs_gmsh_on_background_task_with_stale_guard():
    source = (ROOT / "opencae/controllers/part/mesh_generation.py").read_text(
        encoding="utf-8"
    )
    assert "BackgroundTask(" in source
    assert "_generate_mesh_candidate" in source
    assert "part_fingerprint(current, include_mesh=True)" in source
    assert "busy_cursor" not in source


def test_solver_output_is_coalesced_before_disk_and_monitor_updates():
    source = (ROOT / "opencae/controllers/job_manager.py").read_text(
        encoding="utf-8"
    )
    assert "_pending_output" in source
    assert "setInterval(40)" in source
    assert "64 * 1024" in source
    assert "_flush_pending_output" in source
    assert "update_runtime_fields" in source
    assert "_RUNTIME_JOB_FIELDS" in source
