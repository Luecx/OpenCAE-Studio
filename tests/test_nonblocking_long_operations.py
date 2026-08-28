"""Regression coverage for keeping long-running work away from Qt's GUI thread."""

from __future__ import annotations

from pathlib import Path
from time import sleep

from PyQt6.QtCore import QEventLoop, QThread, QTimer
from PyQt6.QtWidgets import QApplication

from opencae.controllers.background_task import BackgroundTask


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
